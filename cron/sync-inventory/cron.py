"""Synchronise l'inventaire des cartes et tableaux de bord Metabase. Périodique."""

from skills.sync_metabase.scripts.sync_inventory import main
from web.cron_task import run

if __name__ == "__main__":
    run(main)
