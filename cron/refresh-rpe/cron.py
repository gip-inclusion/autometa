"""Rafraîchit le cache des indicateurs du Réseau pour l'emploi. Périodique."""

from lib.rpe import refresh
from web.cron_task import run

if __name__ == "__main__":
    run(refresh)
