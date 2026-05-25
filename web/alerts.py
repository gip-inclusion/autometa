"""Post messages to the shared Slack alert channel."""

import logging

from lib.slack import post_message
from web import config

logger = logging.getLogger(__name__)


def notify_alert_channel(message: str) -> None:
    """Post to SLACK_ALERT_CHANNEL; silent if Slack is not configured."""
    token = config.SLACK_BOT_TOKEN
    channel = config.SLACK_ALERT_CHANNEL
    if not token or not channel:
        return

    try:
        if not post_message(token, channel, message):
            logger.warning("Slack alert not delivered to %s", channel)
    except Exception:  # Why: Slack outage must not break callers (cron runner, request handlers, agent threads).
        logger.exception("Slack alert: error posting to %s", channel)
