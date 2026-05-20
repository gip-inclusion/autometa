from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

import web.otel as otel_module
from web.otel import extract_trace_context, init_otel, inject_trace_headers


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
