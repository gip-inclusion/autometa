"""Manual cron task runner — called by the web UI for on-demand runs."""

import logging
import shutil

from flows.base import record_and_notify, run_cron_subprocess, run_with_recording
from flows.check_s3_backups import check_backup_manifest
from lib.dashboards import run_periodic_cleanup
from lib.webinaires import main as webinaires_main
from skills.sync_metabase.scripts.sync_inventory import main as sync_inventory_main
from skills.sync_sites.scripts.sync_sites import main as sync_sites_main
from web.cron import find_task, prepare_s3_workdir, upload_s3_results
from web.helpers import utcnow
from web.slack_feedback import main as slack_feedback_main

logger = logging.getLogger(__name__)

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
    is_s3 = task.get("source") == "s3"
    started_at = utcnow()
    workdir = None
    status, output, duration_ms = "failure", "", 0

    try:
        if is_s3:
            workdir, pre_hashes = prepare_s3_workdir(slug)
            script, cwd = str(workdir / "cron.py"), str(workdir)
        else:
            script, cwd = task["cron_path"], task["path"]
        status, output, duration_ms = run_cron_subprocess(script, cwd, task["timeout"])
        if is_s3 and status == "success":
            upload_s3_results(slug, workdir, pre_hashes)
    except OSError as e:
        output = f"Error running script: {e}"
    finally:
        if workdir and workdir.exists():
            shutil.rmtree(workdir, ignore_errors=True)

    return record_and_notify(slug, status, output, started_at, duration_ms, trigger)


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
