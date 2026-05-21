import pytest
from fastapi import FastAPI
from opentelemetry import context, trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import web.otel as otel_module
from web.otel import (
    SpanStack,
    extract_trace_context,
    init_otel,
    inject_trace_headers,
    instrument_app,
)


def _new_exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


def test_init_otel_idempotent_without_dsn(mocker):
    mocker.patch("web.otel.config.SENTRY_DSN", "")
    mocker.patch.object(otel_module, "_initialized", False)
    instrument_httpx = mocker.patch("web.otel.HTTPXClientInstrumentor")
    instrument_sql = mocker.patch("web.otel.SQLAlchemyInstrumentor")

    init_otel()
    init_otel()

    instrument_httpx.return_value.instrument.assert_called_once()
    instrument_sql.return_value.instrument.assert_called_once()


def test_init_otel_adds_sentry_processor_when_dsn_set(mocker):
    mocker.patch("web.otel.config.SENTRY_DSN", "https://x@y/z")
    mocker.patch.object(otel_module, "_initialized", False)
    mocker.patch("web.otel.HTTPXClientInstrumentor")
    mocker.patch("web.otel.SQLAlchemyInstrumentor")
    set_textmap = mocker.patch("web.otel.set_global_textmap")
    span_processor = mocker.patch("web.otel.SentrySpanProcessor")
    provider_factory = mocker.patch("web.otel.TracerProvider")

    init_otel()

    provider_factory.return_value.add_span_processor.assert_called_once_with(span_processor.return_value)
    set_textmap.assert_called_once()


def test_tracer_emits_valid_span_after_init(mocker):
    mocker.patch("web.otel.config.SENTRY_DSN", "")
    mocker.patch.object(otel_module, "_initialized", False)
    mocker.patch("web.otel.HTTPXClientInstrumentor")
    mocker.patch("web.otel.SQLAlchemyInstrumentor")
    trace.set_tracer_provider(TracerProvider())

    init_otel()
    tracer = trace.get_tracer("unit")
    with tracer.start_as_current_span("work") as span:
        ctx = span.get_span_context()
        assert ctx.is_valid
        assert ctx.trace_id != 0


def test_instrument_app_raises_when_init_otel_not_called(mocker):
    mocker.patch.object(otel_module, "_initialized", False)
    with pytest.raises(RuntimeError, match="init_otel"):
        instrument_app(FastAPI())


def test_span_stack_pops_in_lifo_order():
    _new_exporter()
    tracer = trace.get_tracer("unit")
    with tracer.start_as_current_span("root") as root:
        root_id = root.get_span_context().span_id
        stack = SpanStack()
        a = stack.push(tracer, "a")
        b = stack.push(tracer, "b")
        assert trace.get_current_span().get_span_context().span_id == b.get_span_context().span_id

        # Pop top: current becomes 'a' (LIFO)
        assert stack.pop() is True
        assert trace.get_current_span().get_span_context().span_id == a.get_span_context().span_id

        # Pop next: current becomes 'root'
        assert stack.pop() is True
        assert trace.get_current_span().get_span_context().span_id == root_id

        # Empty pop is a no-op
        assert stack.pop() is False
        assert not stack


def test_span_stack_close_all_unwinds_remaining_spans():
    _new_exporter()
    tracer = trace.get_tracer("unit")
    with tracer.start_as_current_span("root"):
        stack = SpanStack()
        stack.push(tracer, "a")
        stack.push(tracer, "b")
        stack.push(tracer, "c")
        assert len(stack) == 3
        stack.close_all()
        assert not stack


def test_explicit_parent_context_overrides_current_span():
    """Regression: cli.py must parent its phase spans to "process" via context=process_ctx,
    even when the runner has pushed an attached tool_span as the current span.

    Without context=process_ctx, a span created during the tool_span window would inherit
    tool_span as parent, corrupting the trace tree."""
    exporter = _new_exporter()
    tracer = trace.get_tracer("unit")

    with tracer.start_as_current_span("process") as process_span:
        process_ctx = trace.set_span_in_context(process_span)

        # Simulate the runner pushing a tool_span via context.attach (becomes current).
        tool_span = tracer.start_span("tool")
        tool_token = context.attach(trace.set_span_in_context(tool_span))
        try:
            # cli.py creates a phase span DURING the tool window — must parent to process.
            phase = tracer.start_span("phase", context=process_ctx)
            phase.end()
        finally:
            context.detach(tool_token)
            tool_span.end()

    spans = {s.name: s for s in exporter.get_finished_spans()}
    process_id = spans["process"].context.span_id
    assert spans["phase"].parent.span_id == process_id, "phase must be child of process"
    assert spans["tool"].parent.span_id == process_id, "tool must be child of process"


def test_inject_and_extract_trace_headers_round_trip():
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer("unit")

    with tracer.start_as_current_span("parent") as parent:
        parent_trace_id = parent.get_span_context().trace_id
        headers = inject_trace_headers()

    assert headers

    ctx = extract_trace_context(headers)
    with tracer.start_as_current_span("child", context=ctx) as child:
        assert child.get_span_context().trace_id == parent_trace_id
