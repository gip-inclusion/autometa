"""Balaie le bucket : efface ce que plus rien ne référence, ou le liste seulement (dry run). Périodique."""

from web import config, s3_janitor
from web.cron_task import run


def main() -> None:
    s3_janitor.run(delete=config.S3_JANITOR_DELETE)


if __name__ == "__main__":
    run(main)
