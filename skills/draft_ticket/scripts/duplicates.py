"""Cherche dans le backlog les tickets dont le titre ressemble au titre proposé."""

import argparse

from lib import backlog
from skills.draft_ticket.scripts.common import check_config, run_cli


def run(args: argparse.Namespace) -> str:
    missing = check_config()
    if missing:
        return missing
    found = backlog.find_duplicates(args.title)
    if not found:
        return "Aucun ticket proche."
    return "\n".join(f"- {t['title']} ({t['status']}, {t['shared']} mots communs) {t['url']}" for t in found)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("title", help="titre proposé pour le ticket")
    run_cli(run, parser)


if __name__ == "__main__":
    main()
