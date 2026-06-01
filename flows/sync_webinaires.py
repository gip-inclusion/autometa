from prefect import flow

from flows.base import run_with_recording
from lib.webinaires import main


@flow(name="sync-webinaires", log_prints=True)
def sync_webinaires() -> None:
    run_with_recording("sync-webinaires", main)
