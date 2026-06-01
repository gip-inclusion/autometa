import logging
import os
import shutil
import subprocess
import sys
import time

from prefect import flow

from web import config
from web.cron import (
    discover_from_s3,
    get_app_runs,
    notify_cron_status_change,
    prepare_s3_workdir,
    record_run,
    upload_s3_results,
)
from web.helpers import now_local, utcnow

logger = logging.getLogger(__name__)

MAX_OUTPUT_SIZE = 50_000


def _is_due(schedule: str) -> bool:
    return schedule != "weekly" or now_local().weekday() == 0


def _run_s3_app(app: dict) -> None:
    slug = app["slug"]
    timeout = app["timeout"]
    previous = get_app_runs(slug, limit=1)
    previous_status = previous[0]["status"] if previous else None

    workdir, pre_hashes = prepare_s3_workdir(slug)
    started_at = utcnow()
    t0 = time.monotonic()
    status = "failure"
    output = ""

    try:
        result = subprocess.run(
            [sys.executable, str(workdir / "cron.py")],
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PYTHONPATH": str(config.BASE_DIR)},
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        output = result.stdout
        if result.stderr:
            output += "\n--- stderr ---\n" + result.stderr
        output = output[:MAX_OUTPUT_SIZE]
        status = "success" if result.returncode == 0 else "failure"
        if status == "success":
            upload_s3_results(slug, workdir, pre_hashes)
    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        status = "timeout"
        output = f"Script timed out after {timeout}s"
    except OSError as e:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        output = f"Error running script: {e}"
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    run_result = {
        "slug": slug,
        "status": status,
        "output": output,
        "duration_ms": elapsed_ms,
        "started_at": started_at,
        "finished_at": utcnow(),
    }
    record_run(run_result, "scheduled")
    notify_cron_status_change(slug, status, previous_status, output)


@flow(name="s3-app-crons", log_prints=True)
def s3_app_crons() -> None:
    apps = [a for a in discover_from_s3() if a["enabled"] and _is_due(a["schedule"])]
    logger.info("Running %d S3 app crons", len(apps))
    for app in apps:
        _run_s3_app(app)
