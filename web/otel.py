"""OpenTelemetry setup. Sentry is the backend via SentrySpanProcessor + SentryPropagator."""

import logging

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.trace import TracerProvider
from sentry_sdk.integrations.opentelemetry import SentryPropagator, SentrySpanProcessor

from . import config

logger = logging.getLogger(__name__)

_initialized = False


def init_otel() -> None:
    """Wire OpenTelemetry; Sentry export and propagation activated only when DSN is set."""
    global _initialized
    if _initialized:
        return

    provider = TracerProvider()
    trace.set_tracer_provider(provider)

    if config.SENTRY_DSN:
        provider.add_span_processor(SentrySpanProcessor())
        set_global_textmap(SentryPropagator())
        logger.info("OpenTelemetry initialized with Sentry exporter (httpx + sqlalchemy auto-instrumented)")
    else:
        logger.info("OpenTelemetry initialized without exporter (SENTRY_DSN empty)")

    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()

    _initialized = True


def instrument_app(app) -> None:
    """Attach FastAPI auto-instrumentation. Must run after init_otel and after app is created."""
    if not _initialized:
        return
    FastAPIInstrumentor.instrument_app(app)
