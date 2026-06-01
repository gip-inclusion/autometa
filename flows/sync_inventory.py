from prefect import flow

from flows.base import run_with_recording
from skills.sync_metabase.scripts.sync_inventory import main


@flow(name="sync-inventory", log_prints=True)
def sync_inventory() -> None:
    run_with_recording("sync-inventory", main)
