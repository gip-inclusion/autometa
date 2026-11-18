"""Liste dans le canal d'alertes les tableaux de bord que personne n'ouvre plus. Périodique."""

from web import idle_dashboards
from web.cron_task import run

if __name__ == "__main__":
    run(idle_dashboards.run)
