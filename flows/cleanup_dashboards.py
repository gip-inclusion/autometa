from prefect import flow

from flows.base import run_with_recording
from lib.dashboards import run_periodic_cleanup


@flow(name="cleanup-dashboards", log_prints=True)
def cleanup_dashboards() -> None:
    run_with_recording("cleanup-dashboards", lambda: run_periodic_cleanup(dry_run=True))
