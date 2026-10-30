"""Cherche dans le backlog les tickets dont le titre ressemble au titre proposé."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import backlog  # noqa: E402


def run(args: argparse.Namespace) -> str:
    trouves = backlog.chercher_doublons(args.titre)
    if not trouves:
        return "Aucun ticket proche."
    return "\n".join(f"- {t['titre']} ({t['statut']}, {t['communs']} mots communs) {t['url']}" for t in trouves)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("titre", help="titre proposé pour le ticket")
    print(run(parser.parse_args()))


if __name__ == "__main__":
    main()
