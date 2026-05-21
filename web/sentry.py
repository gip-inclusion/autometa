"""Sentry SDK initialization and helpers."""

import logging

import sentry_sdk
from sentry_sdk.types import Event, Hint

from . import config

logger = logging.getLogger(__name__)


def _before_send(event: Event, hint: Hint) -> Event | None:
    """Drop events when DSN is empty (defensive) and scrub PII from headers."""
    if not config.SENTRY_DSN:
        return None
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        for sensitive in ("x-forwarded-email", "x-forwarded-user", "cookie", "authorization"):
            if sensitive in headers:
                headers[sensitive] = "[filtered]"
    return event


def init_sentry():
    """Initialize Sentry SDK with all integrations. No-op if SENTRY_DSN is empty."""
    if not config.SENTRY_DSN:
        logger.debug("SENTRY_DSN not set, skipping Sentry init")
        return

    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        environment=config.SENTRY_ENVIRONMENT,
        traces_sample_rate=config.SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=config.SENTRY_PROFILES_SAMPLE_RATE,
        send_default_pii=False,
        before_send=_before_send,
        # Why: OpenTelemetry is the tracing primitive; SentrySpanProcessor forwards spans here.
        instrumenter="otel",
        # Attach server_name so we can tell workers apart in multi-process deploys
        server_name=None,
    )
    logger.info(
        "Sentry initialized (env=%s, traces=%.0f%%)", config.SENTRY_ENVIRONMENT, config.SENTRY_TRACES_SAMPLE_RATE * 100
    )


def set_user_context(email: str):
    """Set the Sentry user on the current scope."""
    sentry_sdk.set_user({"email": email})
