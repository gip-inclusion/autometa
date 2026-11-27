"""Signale les tableaux de bord sans visite depuis 60 jours, à archiver. Périodique."""

from web.cron_task import run
from web.unused_dashboards import report_unused_dashboards

if __name__ == "__main__":
    run(report_unused_dashboards)
