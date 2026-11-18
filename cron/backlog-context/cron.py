"""Range le contexte du backlog pour la rédaction de tickets. Périodique."""

from lib.backlog_storage import main
from web.cron_task import run

if __name__ == "__main__":
    run(main)
