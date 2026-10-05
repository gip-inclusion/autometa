"""Borne l'historique des crons : sorties vidées à 30 jours, runs supprimés à un an. Périodique."""

from web.cron import purge_cron_history
from web.cron_task import run

if __name__ == "__main__":
    run(purge_cron_history)
