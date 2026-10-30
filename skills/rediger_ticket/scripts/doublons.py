"""Cherche dans le backlog les tickets dont le titre ressemble au titre proposé."""

import argparse
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import backlog  # noqa: E402
from web import config  # noqa: E402


def run(args: argparse.Namespace) -> str:
    if not config.NOTION_BACKLOG_DB:
        return "NOTION_BACKLOG_DB absent : lecture du backlog impossible (variable d'environnement à renseigner)."
    trouves = backlog.chercher_doublons(args.titre)
    if not trouves:
        return "Aucun ticket proche."
    return "\n".join(f"- {t['titre']} ({t['statut']}, {t['communs']} mots communs) {t['url']}" for t in trouves)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("titre", help="titre proposé pour le ticket")
    try:
        print(run(parser.parse_args()))
    except httpx.HTTPStatusError as erreur:
        sys.exit(f"Notion répond {erreur.response.status_code} : {erreur.response.text[:300]}")
    except httpx.TransportError:
        sys.exit("Notion ne répond pas : réessayer dans une minute.")


if __name__ == "__main__":
    main()
