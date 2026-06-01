"""Prefect scheduler — serves all flows with their cron schedules. Run via: uv run python -m flows.serve"""

from prefect import serve
from prefect.schedules import Cron

from flows.check_s3_backups import check_s3_backups
from flows.cleanup_dashboards import cleanup_dashboards
from flows.s3_app_crons import s3_app_crons
from flows.slack_feedback import slack_feedback
from flows.sync_inventory import sync_inventory
from flows.sync_sites import sync_sites
from flows.sync_webinaires import sync_webinaires

TIMEZONE = "Europe/Paris"


def main() -> None:
    serve(
        sync_sites.to_deployment(name="sync-sites", schedule=Cron("0 2 * * *", timezone=TIMEZONE)),
        sync_inventory.to_deployment(name="sync-inventory", schedule=Cron("0 3 * * *", timezone=TIMEZONE)),
        sync_webinaires.to_deployment(name="sync-webinaires", schedule=Cron("0 4 * * *", timezone=TIMEZONE)),
        slack_feedback.to_deployment(name="slack-feedback", schedule=Cron("0 5 * * 1", timezone=TIMEZONE)),
        check_s3_backups.to_deployment(name="check-s3-backups", schedule=Cron("0 6 * * *", timezone=TIMEZONE)),
        cleanup_dashboards.to_deployment(name="cleanup-dashboards", schedule=Cron("0 6 * * *", timezone=TIMEZONE)),
        s3_app_crons.to_deployment(name="s3-app-crons", schedule=Cron("0 6 * * *", timezone=TIMEZONE)),
    )


if __name__ == "__main__":
    main()
