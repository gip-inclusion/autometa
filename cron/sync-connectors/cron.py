"""Rafraîchit l'inventaire des connecteurs de sources. Périodique."""

from lib.source_inventory import main
from web.cron_task import run

if __name__ == "__main__":
    run(main)
