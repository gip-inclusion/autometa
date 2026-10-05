"""Synchronise les baselines, dimensions, événements et segments Matomo. Périodique."""

from skills.sync_sites.scripts.sync_sites import main
from web.cron_task import run

if __name__ == "__main__":
    run(main)
