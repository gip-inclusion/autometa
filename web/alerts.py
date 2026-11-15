"""Post messages to the shared Slack alert channel."""

import logging

from lib.slack import post_message
from web import config

logger = logging.getLogger(__name__)


def notify_alert_channel(message: str, thread_ts: str | None = None) -> str | None:
    """Post to SLACK_ALERT_CHANNEL in prod, or in the `thread_ts` thread; return the message's ts or None."""
    token = config.SLACK_BOT_TOKEN
    channel = config.SLACK_ALERT_CHANNEL
    if not config.ENV.posts_alerts or not token or not channel:
        return None

    try:
        ts = post_message(token, channel, message if thread_ts else f"[{config.APP_NAME}] {message}", thread_ts)
    except Exception:  # Why: Slack outage must not break callers (cron runner, request handlers, agent threads).
        logger.exception("Slack alert: error posting to %s", channel)
        return None
    if not ts:
        logger.warning("Slack alert not delivered to %s", channel)
    return ts
