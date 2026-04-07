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
        # Attach server_name so we can tell workers apart in multi-process deploys
        server_name=None,
    )
    logger.info(
        "Sentry initialized (env=%s, traces=%.0f%%)", config.SENTRY_ENVIRONMENT, config.SENTRY_TRACES_SAMPLE_RATE * 100
    )


def set_user_context(email: str):
    """Set the Sentry user on the current scope."""
    sentry_sdk.set_user({"email": email})


def set_conversation_context(conversation_id: str, backend: str | None = None):
    """Tag the current scope with conversation metadata."""
    sentry_sdk.set_tag("conversation_id", conversation_id)
    if backend:
        sentry_sdk.set_tag("agent_backend", backend)


def get_trace_headers() -> dict[str, str]:
    """Extract current Sentry trace headers for propagation through Redis."""
    return dict(sentry_sdk.get_current_scope().iter_trace_propagation_headers())


def continue_trace(headers: dict[str, str]) -> sentry_sdk.api.Transaction | None:
    """Continue a Sentry trace from propagated headers (e.g. from Redis payload)."""
    if not config.SENTRY_DSN:
        return None
    return sentry_sdk.continue_trace(headers)
