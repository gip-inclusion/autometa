"""Affiche le contexte des équipes du backlog : équipes produit actives, épics actifs, tickets récents."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import backlog, backlog_stockage  # noqa: E402


def run(args: argparse.Namespace) -> str:
    if args.rafraichir:
        contexte = backlog.charger_contexte()
        backlog_stockage.enregistrer_contexte(contexte)
    else:
        contexte = backlog_stockage.contexte_courant()
    return backlog.formater_contexte(contexte)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rafraichir", action="store_true", help="relire Notion sans attendre le cron")
    print(run(parser.parse_args()))


if __name__ == "__main__":
    main()
