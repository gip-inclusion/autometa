"""OpenTelemetry setup. Sentry is the backend via SentrySpanProcessor + SentryPropagator."""

import logging

from fastapi import FastAPI
from opentelemetry import context, propagate, trace
from opentelemetry.context import Context
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Span, Tracer
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


def instrument_app(app: FastAPI) -> None:
    """Attach FastAPI auto-instrumentation. Raises if init_otel() has not run yet."""
    if not _initialized:
        raise RuntimeError("instrument_app() called before init_otel()")
    FastAPIInstrumentor.instrument_app(app)


def inject_trace_headers() -> dict[str, str]:
    """Serialize the current trace context to HTTP-style headers for cross-process propagation."""
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    return carrier


def extract_trace_context(headers: dict[str, str]) -> Context:
    """Rebuild a trace context from headers produced by inject_trace_headers."""
    return propagate.extract(headers)


class SpanStack:
    """LIFO stack of attached spans for event-driven lifecycles.

    Use when span transitions are triggered by events (stream parsing, async loops)
    where a `with` block doesn't fit. push() and pop() each combine
    span+context lifecycle; close_all() ends everything LIFO on cleanup.

    LIFO is enforced structurally: pop() always removes the top of the stack.
    """

    def __init__(self) -> None:
        self._stack: list[tuple[Span, object]] = []

    def push(self, tracer: Tracer, name: str, **attributes) -> Span:
        span = tracer.start_span(name, attributes=attributes)
        token = context.attach(trace.set_span_in_context(span))
        self._stack.append((span, token))
        return span

    def pop(self) -> bool:
        """Detach + end the topmost span. Returns False if the stack was empty."""
        if not self._stack:
            return False
        span, token = self._stack.pop()
        context.detach(token)
        span.end()
        return True

    def close_all(self) -> None:
        while self._stack:
            self.pop()

    def __bool__(self) -> bool:
        return bool(self._stack)

    def __len__(self) -> int:
        return len(self._stack)
