from prefect import flow

from flows.base import run_with_recording
from web.slack_feedback import main


@flow(name="slack-feedback", log_prints=True)
def slack_feedback() -> None:
    run_with_recording("slack-feedback", main)
