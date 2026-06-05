import logging
import shutil

from prefect import flow

from flows.base import record_and_notify, run_cron_subprocess
from web.cron import discover_from_s3, prepare_s3_workdir, upload_s3_results
from web.helpers import now_local, utcnow

logger = logging.getLogger(__name__)


def _is_due(schedule: str) -> bool:
    return schedule != "weekly" or now_local().weekday() == 0


def _run_s3_app(app: dict) -> None:
    slug = app["slug"]
    workdir, pre_hashes = prepare_s3_workdir(slug)
    started_at = utcnow()
    try:
        status, output, duration_ms = run_cron_subprocess(str(workdir / "cron.py"), str(workdir), app["timeout"])
        if status == "success":
            upload_s3_results(slug, workdir, pre_hashes)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    record_and_notify(slug, status, output, started_at, duration_ms, "scheduled")


@flow(name="s3-app-crons", log_prints=True)
def s3_app_crons() -> None:
    apps = [a for a in discover_from_s3() if a["enabled"] and _is_due(a["schedule"])]
    logger.info("Running %d S3 app crons", len(apps))
    for app in apps:
        _run_s3_app(app)
