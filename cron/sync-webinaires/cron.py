"""Synchronise les webinaires et leurs inscriptions depuis Grist vers le datalake. Périodique."""

from lib.webinaires import main
from web.cron_task import run

if __name__ == "__main__":
    run(main)
