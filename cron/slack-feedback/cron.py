"""Sollicite un retour d'expérience sur Slack auprès des personnes actives. Périodique."""

from web.cron_task import run
from web.slack_feedback import main

if __name__ == "__main__":
    run(main)
