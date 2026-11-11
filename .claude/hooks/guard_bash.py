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
# Why: le corps d'un heredoc est de la donnée — un commentaire « pas de pip install » n'installe rien.
HEREDOC_BODY = re.compile(r"<<-?\s*(['\"]?)(\w+)\1([^\n]*)\n.*?^\s*\2\s*$", re.S | re.M)
OPERATORS = "();<>|&\n"
WRAPPERS = frozenset(("sudo", "env", "nohup", "time", "exec", "command"))
SHELLS = frozenset(("sh", "bash", "zsh", "dash"))
# Why: un téléchargement n'est refusé que s'il vise un paquet ou un binaire (Node.js, roue, .deb), pas une API.
PACKAGE_URL = re.compile(
    r"nodejs\.org/dist|pythonhosted\.org|registry\.npmjs\.org|archive\.ubuntu\.com|chrome-for-testing"
    r"|/releases/download/|\.(?:whl|deb|rpm)(?:[?#]|$)"
)
# Why: une ligne que shlex ne sait pas découper, bash ne l'exécuterait pas non plus ; on la juge sur son texte.
RAW_INSTALL = re.compile(r"\b(?:install|download|ensurepip|npx|dpkg-deb)\b")


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


def simple_commands(command):
    """Les commandes simples de la ligne, chacune avec l'opérateur qui la précède."""
    lexer = shlex.shlex(HEREDOC_BODY.sub(r"\3", command), posix=True, punctuation_chars=OPERATORS)
    lexer.whitespace, lexer.whitespace_split = " \t\r", True
    commands, words, operator = [], [], ""
    for token in lexer:
        if set(token) <= set(OPERATORS):
            if words:
                commands.append((operator, words))
            words, operator = [], token
        else:
            words.append(token)
    if words:
        commands.append((operator, words))
    return commands


def program(words):
    """Le programme et ses arguments, sans affectations ni enveloppes (`sudo`, `env`) ; `python -m x` devient `x`."""
    while words and ("=" in words[0] and not words[0].startswith("-") or Path(words[0]).name in WRAPPERS):
        words = words[1:]
    if len(words) > 2 and re.fullmatch(r"python[\d.]*", Path(words[0]).name) and words[1] == "-m":
        words = words[2:]
    return (Path(words[0]).name, words[1:]) if words else ("", [])


def installs(name, args):
    """Vrai si la commande simple installe ou télécharge un logiciel."""
    words = [arg for arg in args if not arg.startswith("-")]
    if name == "uv" and words[:1] == ["pip"]:
        name, words = "pip", words[1:]
    # Why: les deux premiers mots, pour `npm --prefix /tmp/x install`.
    verbs = set(words[:2])
    if re.fullmatch(r"pip[\d.]*", name) or name in ("apt", "apt-get"):
        return bool(verbs & {"install", "download"})
    if name in ("npm", "yarn", "pnpm", "bun"):
        return bool(verbs & {"i", "install", "add", "ci"})
    if name == "playwright":
        return "install" in verbs
    if name == "dpkg":
        return bool(set(args) & {"-i", "--install"})
    if name in ("curl", "wget"):
        return any(PACKAGE_URL.search(arg) for arg in args)
    return name in ("npx", "bunx", "ensurepip", "dpkg-deb")


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
        if installs(name, args) or (operator == "|" and name in SHELLS and previous in ("curl", "wget")):
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
