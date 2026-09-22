"""Pre-tool-use hook: refuse un `git commit` qui désarme les hooks, cluster de drapeaux compris."""

import json
import re
import shlex
import sys

BLOCK_MSG = (
    "Commande refusée : `git commit` sans les hooks (--no-verify / -n) contourne le lint et la "
    "suite unit que le pre-commit rejoue. Corriger ce que le hook signale, ne pas le désarmer."
)
# Why: un glob de préfixe ne peut pas voir `-nm` ni `-am … -n` — un drapeau court vit dans un cluster.
SHORT_FLAG = re.compile(r"-[a-zA-Z]*n[a-zA-Z]*$")
SEPARATORS = frozenset(("&&", "||", ";", "|", "&"))


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


if __name__ == "__main__":
    data = json.load(sys.stdin)
    msg = verdict(data.get("tool_input", {}).get("command", ""))
    if msg:
        print(msg, file=sys.stderr)
        sys.exit(2)
