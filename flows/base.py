import time
import traceback
from collections.abc import Callable

from web.cron import get_app_runs, notify_cron_status_change, record_run
from web.helpers import utcnow


def run_with_recording(slug: str, fn: Callable, trigger: str = "scheduled") -> dict:
    """Run fn, record result to CronRun, send Slack notification on status change."""
    previous = get_app_runs(slug, limit=1)
    previous_status = previous[0]["status"] if previous else None
    started_at = utcnow()
    t0 = time.monotonic()
    status = "failure"
    output = ""
    exc = None

    try:
        fn()
        status = "success"
    except Exception as e:
        # Why: catch-all — any exception from user scripts must be recorded, not crash the scheduler
        output = traceback.format_exc()
        exc = e

    result = {
        "slug": slug,
        "status": status,
        "output": output,
        "duration_ms": int((time.monotonic() - t0) * 1000),
        "started_at": started_at,
        "finished_at": utcnow(),
    }
    record_run(result, trigger)
    if trigger == "scheduled":
        notify_cron_status_change(slug, status, previous_status, output)

    if exc is not None:
        raise exc
    return result
