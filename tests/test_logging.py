import io
import json
import logging

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from web.log import CorrelationFilter, build_json_formatter, setup_logging
from web.request_context import (
    current_client_ip,
    current_conversation_id,
    current_request_id,
    current_user_id,
)


def _make_record(message: str = "hello", level: int = logging.INFO) -> logging.LogRecord:
    return logging.LogRecord("test", level, "f", 1, message, (), None)


def test_correlation_filter_injects_request_conversation_user_and_ip():
    tokens = [
        current_request_id.set("req-1"),
        current_conversation_id.set("conv-9"),
        current_user_id.set("alice"),
        current_client_ip.set("10.0.0.1"),
    ]
    try:
        record = _make_record()
        CorrelationFilter().filter(record)
    finally:
        current_client_ip.reset(tokens[3])
        current_user_id.reset(tokens[2])
        current_conversation_id.reset(tokens[1])
        current_request_id.reset(tokens[0])

    assert record.request_id == "req-1"
    assert record.conversation_id == "conv-9"
    assert record.user_id == "alice"
    assert record.client_ip == "10.0.0.1"


def test_correlation_filter_picks_up_active_span():
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer("test")

    record = _make_record()
    with tracer.start_as_current_span("unit"):
        CorrelationFilter().filter(record)

    assert record.trace_id is not None
    assert len(record.trace_id) == 32
    assert record.span_id is not None
    assert len(record.span_id) == 16
    assert record.trace_flags is not None


def test_otlp_formatter_emits_core_fields():
    formatter = build_json_formatter()
    record = _make_record("structured", logging.WARNING)
    CorrelationFilter().filter(record)

    payload = json.loads(formatter.format(record))
    assert payload["body"] == "structured"
    assert payload["severity_text"] == "WARNING"
    assert payload["severity_number"] == 13
    assert isinstance(payload["timestamp_unix_nano"], int)
    assert isinstance(payload["observed_timestamp_unix_nano"], int)
    assert payload["instrumentation_scope"] == {"name": "test"}
    assert payload["resource"]["service.name"] == "autometa"
    assert "deployment.environment" in payload["resource"]


def test_otlp_formatter_includes_trace_and_attributes_when_present():
    formatter = build_json_formatter()
    record = _make_record("with-attrs")
    record.trace_id = "deadbeef" * 4
    record.span_id = "cafebabe" * 2
    record.trace_flags = 1
    record.request_id = "r"
    record.conversation_id = "c"
    record.user_id = "u"
    record.client_ip = "1.2.3.4"

    payload = json.loads(formatter.format(record))
    assert payload["trace_id"] == "deadbeef" * 4
    assert payload["span_id"] == "cafebabe" * 2
    assert payload["trace_flags"] == 1
    assert payload["attributes"] == {
        "request.id": "r",
        "session.id": "c",
        "enduser.id": "u",
        "client.address": "1.2.3.4",
    }


def test_otlp_formatter_omits_trace_and_attributes_when_absent():
    formatter = build_json_formatter()
    record = _make_record("bare")
    CorrelationFilter().filter(record)

    payload = json.loads(formatter.format(record))
    assert "trace_id" not in payload
    assert "span_id" not in payload
    assert "attributes" not in payload


def test_otlp_formatter_renders_exception():
    formatter = build_json_formatter()
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = logging.LogRecord("test", logging.ERROR, "f", 1, "fail", (), sys.exc_info())

    payload = json.loads(formatter.format(record))
    assert "exception" in payload
    assert "ValueError: boom" in payload["exception"]


def test_setup_logging_correlates_child_logger_output_with_active_span():
    """A log emitted by a CHILD logger must carry trace_id in JSON output.
    Regression test: a filter on root logger alone would miss these records — only
    handler-level filters fire on child→ancestor handler dispatch."""
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer("test")

    setup_logging(level=logging.INFO)
    buf = io.StringIO()
    for h in logging.root.handlers:
        if isinstance(h, logging.StreamHandler):
            h.stream = buf

    child = logging.getLogger("web.something.child")
    with tracer.start_as_current_span("work") as span:
        expected_trace_id = format(span.get_span_context().trace_id, "032x")
        child.info("hello from child")

    line = buf.getvalue().strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["body"] == "hello from child"
    assert payload["trace_id"] == expected_trace_id, (
        "child-logger records must be enriched too — filter must live on the handler, not the root logger"
    )


def test_setup_logging_suppresses_noisy_third_party_loggers():
    setup_logging(level=logging.INFO)

    assert logging.getLogger("httpx").level >= logging.WARNING
    assert logging.getLogger("httpcore").level >= logging.WARNING
    assert logging.getLogger("paramiko").level >= logging.WARNING


def test_setup_logging_attaches_only_stream_handler():
    setup_logging(level=logging.INFO)

    handler_types = [type(h).__name__ for h in logging.root.handlers]
    assert handler_types == ["StreamHandler"]


@pytest.mark.parametrize("logger_name", ["uvicorn", "uvicorn.error", "uvicorn.access"])
def test_setup_logging_routes_uvicorn_loggers_through_root(logger_name):
    pre = logging.getLogger(logger_name)
    pre.handlers.append(logging.StreamHandler())
    pre.propagate = False

    setup_logging(level=logging.INFO)

    lg = logging.getLogger(logger_name)
    assert lg.handlers == []
    assert lg.propagate is True
