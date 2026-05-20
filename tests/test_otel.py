from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

import web.otel as otel_module
from web.otel import init_otel


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
