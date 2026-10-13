"""Synchronise les tags depuis la base Notion et signale les termes à valider. Périodique."""

from lib.tag_sync import main
from web.cron_task import run

if __name__ == "__main__":
    run(main)
