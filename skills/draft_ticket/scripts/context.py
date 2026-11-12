"""Affiche le contexte des équipes du backlog : équipes produit actives, épics actifs, tickets récents."""

import argparse

from lib import backlog, backlog_storage
from skills.draft_ticket.scripts.common import check_config, run_cli


def run(args: argparse.Namespace) -> str:
    missing = check_config()
    if missing:
        return missing
    if args.refresh:
        context = backlog.load_context()
        backlog_storage.save_context(context)
    else:
        context = backlog_storage.current_context()
    return backlog.format_context(context)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="relire Notion sans attendre le cron")
    run_cli(run, parser)


if __name__ == "__main__":
    main()
