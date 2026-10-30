"""Range chaque jour le contexte des équipes du backlog pour la rédaction de tickets. Périodique."""

from lib.backlog_stockage import main
from web.cron_task import run

if __name__ == "__main__":
    run(main)
