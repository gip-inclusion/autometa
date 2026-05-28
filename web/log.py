"""Structured logging emitting OTLP/JSON records on stdout.

Each log line is a JSON object following the OpenTelemetry log data model
(timestamp_unix_nano, severity_*, body, resource, instrumentation_scope, attributes).
Trace/span context comes from the active OpenTelemetry span; request/conversation/
user/client context comes from contextvars set by middleware. Scalingo's log drain
ships stdout to Datadog (no in-process forwarder).
"""

import json
import logging
import time

from opentelemetry import trace

from . import config
from .request_context import current_client_ip, current_conversation_id, current_request_id, current_user_id

logger = logging.getLogger(__name__)

_SEVERITY_NUMBER = {
    logging.DEBUG: 5,
    logging.INFO: 9,
    logging.WARNING: 13,
    logging.ERROR: 17,
    logging.CRITICAL: 21,
}

_ATTRIBUTE_KEYS = (
    ("request_id", "request.id"),
    ("conversation_id", "session.id"),
    ("user_id", "enduser.id"),
    ("client_ip", "client.address"),
)


class CorrelationFilter(logging.Filter):
    """Inject trace/span/request/conversation/user/client ids onto every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = trace.get_current_span().get_span_context()
        if ctx.is_valid:
            record.trace_id = format(ctx.trace_id, "032x")
            record.span_id = format(ctx.span_id, "016x")
            record.trace_flags = ctx.trace_flags
        else:
            record.trace_id = None
            record.span_id = None
            record.trace_flags = None
        record.request_id = current_request_id.get()
        record.conversation_id = current_conversation_id.get()
        record.user_id = current_user_id.get()
        record.client_ip = current_client_ip.get()
        return True


class OTLPJSONFormatter(logging.Formatter):
    """Emit OTLP/JSON-conformant log records per the OpenTelemetry log data model."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "timestamp_unix_nano": int(record.created * 1_000_000_000),
            "observed_timestamp_unix_nano": time.time_ns(),
            "severity_number": _SEVERITY_NUMBER.get(record.levelno, 0),
            "severity_text": record.levelname,
            "body": record.getMessage(),
            "instrumentation_scope": {"name": record.name},
            "resource": {
                "service.name": "autometa",
                "deployment.environment": config.SENTRY_ENVIRONMENT,
            },
        }
        trace_id = getattr(record, "trace_id", None)
        span_id = getattr(record, "span_id", None)
        if trace_id and span_id:
            entry["trace_id"] = trace_id
            entry["span_id"] = span_id
            trace_flags = getattr(record, "trace_flags", None)
            if trace_flags is not None:
                entry["trace_flags"] = trace_flags
        attributes = {
            otel_key: getattr(record, src, None) for src, otel_key in _ATTRIBUTE_KEYS if getattr(record, src, None)
        }
        if attributes:
            entry["attributes"] = attributes
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def build_json_formatter() -> logging.Formatter:
    """OTLP/JSON formatter for the console handler."""
    return OTLPJSONFormatter()


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with OTLP/JSON output and a correlation filter on the handler."""
    formatter = build_json_formatter()
    correlation = CorrelationFilter()

    # Why: filter must be on the HANDLER, not on the root logger. Logger.callHandlers walks up
    # the parent chain and dispatches to ancestors' handlers (with their filters) but does NOT
    # re-apply ancestors' logger-level filters. A filter on root would skip records from any
    # child logger — i.e. almost everything in this codebase.
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.addFilter(correlation)

    logging.root.handlers.clear()
    logging.root.addHandler(console)
    logging.root.setLevel(level)

    # Why: uvicorn attaches text handlers to its own loggers before web.app is imported. Strip
    # them and force propagation so access/error records flow through root's JSON formatter and
    # pick up the correlation fields.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("paramiko").setLevel(logging.WARNING)
