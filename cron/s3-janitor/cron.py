"""Balaie le bucket, puis liste les tableaux de bord que personne n'ouvre plus. Périodique."""

from web import config, idle_dashboards, s3_janitor
from web.cron_task import run


def main() -> None:
    s3_janitor.run(delete=config.S3_JANITOR_DELETE)
    idle_dashboards.run()


if __name__ == "__main__":
    run(main)
