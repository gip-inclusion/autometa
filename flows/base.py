import os
import subprocess
import sys
import time
import traceback
from collections.abc import Callable

from web import config
from web.cron import get_app_runs, notify_cron_status_change, record_run
from web.helpers import utcnow

MAX_OUTPUT_SIZE = 50_000


def run_cron_subprocess(script: str, cwd: str, timeout: int) -> tuple[str, str, int]:
    """Run a cron script as a subprocess; return (status, output, duration_ms)."""
    t0 = time.monotonic()
    try:
        result = subprocess.run(
            [sys.executable, script],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PYTHONPATH": str(config.BASE_DIR)},
        )
        output = result.stdout
        if result.stderr:
            output += "\n--- stderr ---\n" + result.stderr
        status = "success" if result.returncode == 0 else "failure"
    except subprocess.TimeoutExpired:
        status, output = "timeout", f"Script timed out after {timeout}s"
    except OSError as e:
        status, output = "failure", f"Error running script: {e}"
    return status, output[:MAX_OUTPUT_SIZE], int((time.monotonic() - t0) * 1000)


def record_and_notify(slug: str, status: str, output: str, started_at, duration_ms: int, trigger: str) -> dict:
    """Persist a CronRun and, for scheduled runs, alert Slack on a status change."""
    previous_status = None
    if trigger == "scheduled":
        previous = get_app_runs(slug, limit=1)
        previous_status = previous[0]["status"] if previous else None
    result = {
        "slug": slug,
        "status": status,
        "output": output,
        "duration_ms": duration_ms,
        "started_at": started_at,
        "finished_at": utcnow(),
    }
    record_run(result, trigger)
    if trigger == "scheduled":
        notify_cron_status_change(slug, status, previous_status, output)
    return result


def run_with_recording(slug: str, fn: Callable, trigger: str = "scheduled") -> dict:
    """Run fn, record result to CronRun, send Slack notification on status change."""
    started_at = utcnow()
    t0 = time.monotonic()
    status = "success"
    output = ""
    exc = None
    try:
        fn()
    except Exception as e:
        # Why: catch-all — any exception from user scripts must be recorded, not crash the scheduler
        status = "failure"
        output = traceback.format_exc()
        exc = e

    result = record_and_notify(slug, status, output, started_at, int((time.monotonic() - t0) * 1000), trigger)
    if exc is not None:
        raise exc
    return result
