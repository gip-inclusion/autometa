"""Rattrape les objets restés sans suggestion de tags, par petits lots et sur un budget de temps."""

from lib.tag_suggestions import catch_up
from web.cron_task import run

if __name__ == "__main__":
    run(catch_up)
