"""Sentry SDK initialization and helpers."""

import logging
import re

import sentry_sdk
from sentry_sdk.types import Event, Hint

from . import config

logger = logging.getLogger(__name__)

# Why: defensive scrubbing of secret patterns that may leak from CLI stderr / last_events
# / prompt snippets into Sentry events. Not a replacement for not-logging-secrets at the source,
# but a backstop for surfaces we don't fully control (Claude CLI stderr, user-pasted prompts).
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Bearer\s+[\w\-\._~+/]+=*", re.IGNORECASE),
    re.compile(r"sk-(?:ant-)?[a-zA-Z0-9_\-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(api[-_]?key|token|password|secret|auth)[\s=:\"']+[\w\-\.]{6,}"),
)
_SENSITIVE_HEADERS = ("x-forwarded-email", "x-forwarded-user", "cookie", "authorization")


def _scrub_string(value: str) -> str:
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub("[scrubbed]", value)
    return value


def _scrub_value(value):
    if isinstance(value, str):
        return _scrub_string(value)
    if isinstance(value, list):
        return [_scrub_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _scrub_value(v) for k, v in value.items()}
    return value


def _before_send(event: Event, hint: Hint) -> Event | None:
    """Drop events when DSN is empty; scrub PII headers and secret patterns from extras."""
    if not config.SENTRY_DSN:
        return None
    headers = event.get("request", {}).get("headers")
    if headers:
        for sensitive in _SENSITIVE_HEADERS:
            if sensitive in headers:
                headers[sensitive] = "[filtered]"
    extras = event.get("extra")
    if extras:
        for key, value in list(extras.items()):
            extras[key] = _scrub_value(value)
    return event


def _before_send_transaction(event: Event, hint: Hint) -> Event | None:
    """Scrub secret patterns from span attributes exported via SentrySpanProcessor."""
    if not config.SENTRY_DSN:
        return None
    trace_data = event.get("contexts", {}).get("trace", {}).get("data")
    if trace_data:
        for key, value in list(trace_data.items()):
            trace_data[key] = _scrub_value(value)
    for span in event.get("spans") or []:
        data = span.get("data")
        if data:
            for key, value in list(data.items()):
                data[key] = _scrub_value(value)
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
        before_send_transaction=_before_send_transaction,
        # Why: OpenTelemetry is the tracing primitive; SentrySpanProcessor forwards spans here.
        instrumenter="otel",
    )
    logger.info(
        "Sentry initialized (env=%s, traces=%.0f%%)", config.SENTRY_ENVIRONMENT, config.SENTRY_TRACES_SAMPLE_RATE * 100
    )


def set_user_context(email: str):
    """Set the Sentry user on the current scope."""
    sentry_sdk.set_user({"email": email})
