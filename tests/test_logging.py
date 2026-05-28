import json
import logging
import time

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from web.log import CorrelationFilter, DatadogHandler, build_json_formatter, setup_logging
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


def test_json_formatter_serializes_correlation_fields():
    formatter = build_json_formatter()
    record = _make_record("structured")
    record.trace_id = "deadbeef" * 4
    record.span_id = "cafebabe" * 2
    record.request_id = "r"
    record.conversation_id = "c"

    payload = json.loads(formatter.format(record))
    assert payload["message"] == "structured"
    assert payload["level"] == "INFO"
    assert payload["trace_id"] == "deadbeef" * 4
    assert payload["span_id"] == "cafebabe" * 2
    assert payload["request_id"] == "r"
    assert payload["conversation_id"] == "c"


def test_datadog_handler_queues_and_sends(mocker):
    mocker.patch("web.config.HOST", "test-host")
    mock_post = mocker.patch("httpx.Client.post")

    handler = DatadogHandler("fake-key", flush_interval=0.1)

    handler.emit(_make_record("hello", logging.WARNING))

    time.sleep(0.3)
    handler.close()

    assert mock_post.call_count >= 1
    payload = json.loads(mock_post.call_args.kwargs["content"])
    assert payload[0]["hostname"] == "test-host"
    assert payload[0]["service"] == "autometa"
    assert payload[0]["level"] == "WARNING"
    assert payload[0]["message"] == "hello"
    assert mock_post.call_args.kwargs["headers"]["DD-API-KEY"] == "fake-key"


def test_datadog_entry_carries_correlation_ids_from_filter_chain(mocker):
    """End-to-end: ContextVars + active span → CorrelationFilter → DatadogHandler → payload."""
    mocker.patch("web.config.HOST", "test-host")
    mock_post = mocker.patch("httpx.Client.post")

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer("test")

    handler = DatadogHandler("k", flush_interval=0.1)

    tokens = [
        current_request_id.set("req-99"),
        current_conversation_id.set("conv-3"),
        current_user_id.set("alice"),
        current_client_ip.set("10.0.0.1"),
    ]
    try:
        with tracer.start_as_current_span("unit") as span:
            expected_trace_id = format(span.get_span_context().trace_id, "032x")
            expected_span_id = format(span.get_span_context().span_id, "016x")
            record = _make_record("boom", logging.ERROR)
            CorrelationFilter().filter(record)
            handler.emit(record)
    finally:
        current_client_ip.reset(tokens[3])
        current_user_id.reset(tokens[2])
        current_conversation_id.reset(tokens[1])
        current_request_id.reset(tokens[0])

    time.sleep(0.3)
    handler.close()

    payload = json.loads(mock_post.call_args.kwargs["content"])[0]
    assert payload["trace_id"] == expected_trace_id
    assert payload["span_id"] == expected_span_id
    assert payload["request_id"] == "req-99"
    assert payload["conversation_id"] == "conv-3"
    assert payload["user_id"] == "alice"
    assert payload["client_ip"] == "10.0.0.1"


def test_datadog_handler_survives_network_error(mocker):
    mocker.patch("web.config.HOST", "test-host")
    mocker.patch("httpx.Client.post", side_effect=ConnectionError("down"))

    handler = DatadogHandler("fake-key", flush_interval=0.1)

    handler.emit(_make_record("boom", logging.ERROR))

    time.sleep(0.3)
    handler.close()


def test_setup_logging_adds_datadog_handler_when_configured(mocker):
    mocker.patch("web.config.DATADOG_API_KEY", "test-key")
    mocker.patch("web.config.HOST", "test-host")
    mocker.patch("httpx.Client.post")

    setup_logging(level=logging.INFO)

    handler_types = [type(h).__name__ for h in logging.root.handlers]
    assert "StreamHandler" in handler_types
    assert "DatadogHandler" in handler_types

    for h in logging.root.handlers[:]:
        if isinstance(h, DatadogHandler):
            h.close()
            logging.root.removeHandler(h)


def test_setup_logging_correlates_child_logger_output_with_active_span(mocker):
    """A log emitted by a CHILD logger (typical case) must carry trace_id in JSON output.
    Regression test: a filter on root logger alone would miss these records — only
    handler-level filters fire on child→ancestor handler dispatch."""
    import io

    mocker.patch("web.config.DATADOG_API_KEY", "")
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
    assert payload["message"] == "hello from child"
    assert payload["trace_id"] == expected_trace_id, (
        "child-logger records must be enriched too — filter must live on the handler, not the root logger"
    )


def test_setup_logging_suppresses_httpx_logs(mocker):
    mocker.patch("web.config.DATADOG_API_KEY", "test-key")
    mocker.patch("web.config.HOST", "test-host")
    mocker.patch("httpx.Client.post")

    setup_logging(level=logging.INFO)

    assert logging.getLogger("httpx").level >= logging.WARNING
    assert logging.getLogger("httpcore").level >= logging.WARNING
    assert logging.getLogger("paramiko").level >= logging.WARNING

    for h in logging.root.handlers[:]:
        if isinstance(h, DatadogHandler):
            h.close()
            logging.root.removeHandler(h)


def test_setup_logging_no_datadog_without_key(mocker):
    mocker.patch("web.config.DATADOG_API_KEY", "")

    setup_logging(level=logging.INFO)

    handler_types = [type(h).__name__ for h in logging.root.handlers]
    assert "StreamHandler" in handler_types
    assert "DatadogHandler" not in handler_types
