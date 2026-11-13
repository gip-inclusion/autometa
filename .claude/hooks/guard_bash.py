"""Pre-tool-use hook: refuse un `git commit` qui désarme les hooks et, sur les serveurs, toute installation de logiciel."""

import json
import re
import shlex
import sys
from pathlib import Path

from hook_env import is_server

BLOCK_MSG = (
    "Commande refusée : `git commit` sans les hooks (--no-verify / -n) contourne le lint et la "
    "suite unit que le pre-commit rejoue. Corriger ce que le hook signale, ne pas le désarmer."
)
BLOCK_INSTALL_MSG = (
    "Commande refusée : aucune installation de logiciel dans le conteneur (paquet pip, npm ou apt, binaire, "
    "navigateur ou archive téléchargés). Le code téléchargé tourne avec tous les secrets du conteneur, et /tmp est "
    "partagé entre les conversations. Si un outil manque, le dire à l'utilisateur ; les outils présents sont listés "
    "dans AGENT.md, section « Environnement container »."
)
# Why: un glob de préfixe ne peut pas voir `-nm` ni `-am … -n` — un drapeau court vit dans un cluster.
SHORT_FLAG = re.compile(r"-[a-zA-Z]*n[a-zA-Z]*$")
SEPARATORS = frozenset(("&&", "||", ";", "|", "&"))
# Why: le corps d'un heredoc est de la donnée — un commentaire « pas de pip install » n'installe rien —, sauf quand
# un shell le lit (`bash <<EOF`).
HEREDOC = re.compile(r"^([^\n]*?)<<-?\s*(['\"]?)(\w+)\2([^\n]*)\n(.*?)^\s*\3\s*$", re.S | re.M)
# Why: un `#` en début de mot ouvre un commentaire jusqu'à la fin de la ligne ; ailleurs (`a#b`, URL à ancre) et entre
# guillemets, c'est du texte. shlex le prend pour un commentaire partout et mange le saut de ligne qui le clôt.
COMMENT = re.compile(r"""('[^']*'|"(?:\\.|[^"\\])*")|(?<![^\s;|&()])#[^\n]*""")
OPERATORS = "();<>|&\n"
# Why: une redirection et sa cible ne sont ni une commande ni un argument ; lue comme une commande, la cible de
# `2>/dev/null` cachait le `curl` de `curl … 2>/dev/null | sh`. `<(` et `<<<` restent des séparateurs.
REDIRECTION = re.compile(r"&?[<>]{1,2}&?")
# Why: un shell exécute le mot qui suit `-c`, aussi dans un cluster de drapeaux courts (`bash -lc`).
SHELL_SCRIPT_FLAG = re.compile(r"-[a-zA-Z]*c[a-zA-Z]*")
# Why: ce qui précède le programme lancé — mots-clés du shell, enveloppes (`sudo -E`, `timeout 120`, `xargs`).
PREFIXES = frozenset(("if", "then", "else", "elif", "while", "until", "do", "!", "{", "time", "sudo", "env", "nohup"))
PREFIXES |= frozenset(("exec", "command", "timeout", "nice", "xargs", "stdbuf"))
SHELLS = frozenset(("sh", "bash", "zsh", "dash"))
DOWNLOADERS = frozenset(("curl", "wget"))
# Why: un téléchargement n'est refusé que s'il vise un paquet ou un binaire (Node.js, roue, .deb), pas une API.
PACKAGE_URL = re.compile(
    r"nodejs\.org/dist|pythonhosted\.org|registry\.npmjs\.org|archive\.ubuntu\.com|chrome-for-testing"
    r"|/releases/download/|\.(?:whl|deb|rpm)(?:[?#]|$)"
)
# Why: une ligne que shlex ne sait pas découper, bash ne l'exécuterait pas non plus ; on la juge sur son texte.
RAW_INSTALL = re.compile(r"\b(?:install|download|ensurepip|npx|uvx|dpkg-deb)\b")


def ends_the_command(token):
    """Un séparateur, ou une redirection dont la suite est de la donnée — un corps de heredoc."""
    return token in SEPARATORS or token.startswith(("<", ">"))


def disarms(token):
    return token == "--no-verify" or bool(SHORT_FLAG.fullmatch(token))


def commit_starts_at(tokens, index):
    """Position du sous-commandement `commit`, en sautant les options globales `-c cle=valeur`."""
    position = index + 1
    while position < len(tokens) and tokens[position] == "-c":
        position += 2
    return position if position < len(tokens) and tokens[position] == "commit" else None


def verdict(command):
    """Le message de refus, ou None — fail-open sur une ligne que shlex ne sait pas découper."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    for index, token in enumerate(tokens):
        start = commit_starts_at(tokens, index) if token == "git" else None
        if start is None:
            continue
        for candidate in tokens[start + 1 :]:
            if ends_the_command(candidate):
                break
            if disarms(candidate):
                return BLOCK_MSG
    return None


def heredoc_read_by_shell(match):
    """Le heredoc sans son corps, sauf si un shell le lit."""
    prefix, rest, body = match.group(1, 4, 5)
    read_by_shell = SHELLS & {Path(word).name for word in re.split(r"[\s;|&()]+", prefix + rest)}
    return prefix + rest + ("\n" + body if read_by_shell else "")


def simple_commands(command):
    """Les commandes simples de la ligne, sans leurs redirections, chacune avec l'opérateur qui la précède."""
    code = COMMENT.sub(r"\1", HEREDOC.sub(heredoc_read_by_shell, command))
    lexer = shlex.shlex(code, posix=True, punctuation_chars=OPERATORS)
    lexer.whitespace, lexer.whitespace_split, lexer.commenters = " \t\r", True, ""
    commands, words, operator, target = [], [], "", False
    for token in lexer:
        if target:
            target = False
        elif REDIRECTION.fullmatch(token):
            target = True
            if words and words[-1].isdigit():
                words.pop()
        elif set(token) <= set(OPERATORS):
            if words:
                commands.append((operator, words))
            words, operator = [], token
        else:
            words.append(token)
    if words:
        commands.append((operator, words))
    return commands


def program(words):
    """Le programme lancé et ses arguments, après mots-clés, enveloppes et affectations ; `python -m x` devient `x`."""
    while words and (
        Path(words[0]).name in PREFIXES
        or words[0].startswith("-")
        or "=" in words[0]
        or re.fullmatch(r"\d+[smhd]?", words[0])
    ):
        # Why: `command -v x` dit si x existe, comme `which x` ; seul `command x` lance x.
        if words[:2] in (["command", "-v"], ["command", "-V"]):
            break
        words = words[1:]
    if not words:
        return "", []
    name, args = Path(words[0]).name, words[1:]
    if re.fullmatch(r"python[\d.]*", name) and "-m" in args[:-1]:
        module = args.index("-m") + 1
        return args[module], args[module + 1 :]
    return name, args


def installs(name, args):
    """Vrai si la commande simple installe ou télécharge un logiciel."""
    # Why: le premier mot en minuscules, pas le premier argument — `npm --prefix /tmp/x install`, `pip -q install`.
    verb = next((arg for arg in args if re.fullmatch(r"[a-z]+", arg)), "")
    if re.fullmatch(r"pip[\d.]*", name) or name in ("apt", "apt-get"):
        return verb in ("install", "download")
    if name in ("npm", "yarn", "pnpm", "bun"):
        return verb in ("i", "install", "add", "ci", "exec", "x", "dlx")
    if name == "uv" and verb == "run":
        # Why: `uv run --with x` installe x depuis PyPI avant de lancer la commande.
        return any(arg.startswith("--with") for arg in args)
    if name == "uv":
        return verb in ("add", "tool") or verb == "pip" and installs("pip", args[args.index("pip") + 1 :])
    if name == "pipx":
        return verb in ("install", "run")
    if name == "playwright":
        return verb == "install"
    if name == "dpkg":
        return bool(set(args) & {"-i", "--install"})
    if name in DOWNLOADERS:
        return any(PACKAGE_URL.search(arg) for arg in args)
    return name in ("npx", "bunx", "uvx", "ensurepip", "dpkg-deb")


def runs_stdin(name, args):
    """Vrai si la commande exécute ce qu'elle lit sur son entrée : un shell, ou python sans script ni `-c`."""
    python = re.fullmatch(r"python[\d.]*", name)
    return name in SHELLS or bool(python) and all(arg.startswith("-") and arg not in ("-c", "-m") for arg in args)


def install_verdict(command, on_server):
    """Le message de refus d'une installation sur un serveur, ou None."""
    if not on_server:
        return None
    try:
        commands = simple_commands(command)
    except ValueError:
        return BLOCK_INSTALL_MSG if RAW_INSTALL.search(command) else None
    previous = ""
    for operator, words in commands:
        name, args = program(words)
        # Why: `curl … | sh` et `bash <(curl …)` exécutent ce qu'ils téléchargent, quelle qu'en soit l'adresse.
        fetched_and_run = (operator == "|" and previous in DOWNLOADERS and runs_stdin(name, args)) or (
            operator == "<(" and previous in SHELLS and name in DOWNLOADERS
        )
        flag = next((i for i, arg in enumerate(args[:-1]) if SHELL_SCRIPT_FLAG.fullmatch(arg)), None)
        script = args[flag + 1] if name in SHELLS and flag is not None else ""
        # Why: `bash <<< '…'` lit son script sur l'entrée, comme un heredoc.
        if operator == "<<<" and previous in SHELLS:
            script = words[0]
        if installs(name, args) or fetched_and_run or install_verdict(script, on_server):
            return BLOCK_INSTALL_MSG
        previous = name
    return None


if __name__ == "__main__":
    data = json.load(sys.stdin)
    command = data.get("tool_input", {}).get("command", "")
    msg = verdict(command) or install_verdict(command, is_server())
    if msg:
        print(msg, file=sys.stderr)
        sys.exit(2)
