"""Rappelle dans Slack les PR ouvertes d'Autometa. Du lundi au vendredi."""

from datetime import date

from web.cron_task import run
from web.pr_reminder import remind

if __name__ == "__main__":
    run(lambda: remind(date.today()))
