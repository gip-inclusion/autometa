from prefect import flow

from flows.base import run_with_recording
from skills.sync_sites.scripts.sync_sites import main


@flow(name="sync-sites", log_prints=True)
def sync_sites() -> None:
    run_with_recording("sync-sites", main)
