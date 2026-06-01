"""Manual cron task runner — called by the web UI for on-demand runs."""

import logging
import os
import shutil
import subprocess
import sys
import time

from flows.base import run_with_recording
from flows.check_s3_backups import check_backup_manifest
from lib.dashboards import run_periodic_cleanup
from lib.webinaires import main as webinaires_main
from skills.sync_metabase.scripts.sync_inventory import main as sync_inventory_main
from skills.sync_sites.scripts.sync_sites import main as sync_sites_main
from web import config
from web.cron import (
    find_task,
    get_app_runs,
    notify_cron_status_change,
    prepare_s3_workdir,
    record_run,
    upload_s3_results,
)
from web.helpers import utcnow
from web.slack_feedback import main as slack_feedback_main

logger = logging.getLogger(__name__)

MAX_OUTPUT_SIZE = 50_000

_SYSTEM_RUNNERS: dict[str, object] = {
    "sync-sites": sync_sites_main,
    "sync-inventory": sync_inventory_main,
    "sync-webinaires": webinaires_main,
    "slack-feedback": slack_feedback_main,
    "check-s3-backups": check_backup_manifest,
    "cleanup-dashboards": lambda: run_periodic_cleanup(dry_run=True),
}


def _run_app_task(task: dict, trigger: str) -> dict:
    slug = task["slug"]
    timeout = task["timeout"]
    is_s3 = task.get("source") == "s3"

    previous = get_app_runs(slug, limit=1)
    previous_status = previous[0]["status"] if previous else None
    started_at = utcnow()
    t0 = time.monotonic()
    elapsed_ms = 0
    workdir = None
    pre_hashes: dict[str, str] = {}
    status = "failure"
    output = ""

    try:
        if is_s3:
            workdir, pre_hashes = prepare_s3_workdir(slug)
            cron_script = str(workdir / "cron.py")
            cwd = str(workdir)
        else:
            cron_script = task["cron_path"]
            cwd = task["path"]

        result = subprocess.run(
            [sys.executable, cron_script],
            cwd=cwd,
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
        if is_s3 and status == "success" and workdir:
            upload_s3_results(slug, workdir, pre_hashes)
    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        status = "timeout"
        output = f"Script timed out after {timeout}s"
    except OSError as e:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        output = f"Error running script: {e}"
    finally:
        if workdir and workdir.exists():
            shutil.rmtree(workdir, ignore_errors=True)

    run_result = {
        "slug": slug,
        "status": status,
        "output": output,
        "duration_ms": elapsed_ms,
        "started_at": started_at,
        "finished_at": utcnow(),
    }
    record_run(run_result, trigger)
    if trigger == "scheduled":
        notify_cron_status_change(slug, status, previous_status, output)
    return run_result


def run_cron_task(slug: str, trigger: str = "manual") -> dict:
    """Run a cron task by slug. System tasks call Python functions directly; app tasks use subprocess."""
    task = find_task(slug)
    if not task:
        now = utcnow()
        return {
            "slug": slug,
            "status": "failure",
            "output": f"cron task not found: {slug}",
            "duration_ms": 0,
            "started_at": now,
            "finished_at": now,
        }

    if task["tier"] == "system":
        fn = _SYSTEM_RUNNERS.get(slug)
        if fn is None:
            now = utcnow()
            return {
                "slug": slug,
                "status": "failure",
                "output": f"no runner registered for system task: {slug}",
                "duration_ms": 0,
                "started_at": now,
                "finished_at": now,
            }
        return run_with_recording(slug, fn, trigger)

    return _run_app_task(task, trigger)
