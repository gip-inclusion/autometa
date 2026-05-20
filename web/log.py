"""Structured JSON logging with trace correlation and Datadog forwarding.

Every log record is enriched with trace_id/span_id from the current OpenTelemetry
span and with request_id/conversation_id from contextvars. When DATADOG_API_KEY
is set, records are also forwarded to Datadog HTTP intake.
"""

import atexit
import json
import logging
import queue
import threading

import httpx
from opentelemetry import trace
from pythonjsonlogger import json as json_logger

from . import config
from .request_context import current_client_ip, current_conversation_id, current_request_id, current_user_id

logger = logging.getLogger(__name__)


class CorrelationFilter(logging.Filter):
    """Inject trace_id/span_id/request_id/conversation_id onto every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        span = trace.get_current_span()
        ctx = span.get_span_context() if span else None
        if ctx and ctx.is_valid:
            record.trace_id = format(ctx.trace_id, "032x")
            record.span_id = format(ctx.span_id, "016x")
        else:
            record.trace_id = None
            record.span_id = None
        record.request_id = current_request_id.get()
        record.conversation_id = current_conversation_id.get()
        record.user_id = current_user_id.get()
        record.client_ip = current_client_ip.get()
        return True


def _record_to_datadog_entry(record: logging.LogRecord, message: str) -> dict:
    entry = {
        "message": message,
        "ddsource": "python",
        "service": "autometa",
        "hostname": config.HOST,
        "ddtags": "env:prod",
        "level": record.levelname,
        "logger": {"name": record.name},
    }
    for field in ("trace_id", "span_id", "request_id", "conversation_id", "user_id", "client_ip"):
        value = getattr(record, field, None)
        if value is not None:
            entry[field] = value
    return entry


class DatadogHandler(logging.Handler):
    """Async-buffered handler that sends structured logs to Datadog HTTP intake."""

    def __init__(self, api_key: str, *, batch_size: int = 50, flush_interval: float = 5.0):
        super().__init__()
        self._api_key = api_key
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._queue: queue.Queue[dict] = queue.Queue(maxsize=10_000)
        self._dropped_count = 0
        self._shutdown = threading.Event()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        atexit.register(self.close)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._queue.put_nowait(_record_to_datadog_entry(record, self.format(record)))
        except queue.Full:
            # Drop log message rather than blocking the application when buffer is full.
            self._dropped_count += 1

    def _worker(self) -> None:
        client = httpx.Client(timeout=10)
        while not self._shutdown.is_set():
            batch = self._drain(self._batch_size)
            if not batch:
                self._shutdown.wait(self._flush_interval)
                continue
            self._send(client, batch)
        batch = self._drain(self._batch_size)
        if batch:
            self._send(client, batch)
        client.close()

    def _drain(self, max_items: int) -> list[dict]:
        items: list[dict] = []
        while len(items) < max_items:
            try:
                items.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return items

    def _send(self, client: httpx.Client, batch: list[dict]) -> None:
        try:
            client.post(
                "https://http-intake.logs.datadoghq.eu/api/v2/logs",
                content=json.dumps(batch),
                headers={
                    "DD-API-KEY": self._api_key,
                    "Content-Type": "application/json",
                },
            )
        except httpx.RequestError as e:
            logger.debug("Datadog send failed: %s", e)
        except Exception:
            logger.warning("Datadog send unexpected error", exc_info=True)

    def close(self) -> None:
        self._shutdown.set()
        self._thread.join(timeout=5)
        if self._dropped_count:
            logger.warning("Datadog handler dropped %d log messages (queue full)", self._dropped_count)
        super().close()


def build_json_formatter() -> logging.Formatter:
    """Build the structured JSON formatter used by both console and Datadog handlers."""
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s %(trace_id)s %(span_id)s %(request_id)s %(conversation_id)s %(user_id)s %(client_ip)s"
    return json_logger.JsonFormatter(fmt, rename_fields={"levelname": "level", "asctime": "timestamp"})


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with JSON output and a correlation filter."""
    formatter = build_json_formatter()
    correlation = CorrelationFilter()

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.addFilter(correlation)

    logging.root.handlers.clear()
    logging.root.addHandler(console)
    logging.root.addFilter(correlation)
    logging.root.setLevel(level)

    # Why: each Datadog POST generates an httpx log; INFO would create a feedback loop.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("paramiko").setLevel(logging.WARNING)

    if config.DATADOG_API_KEY:
        dd = DatadogHandler(config.DATADOG_API_KEY)
        dd.setFormatter(formatter)
        dd.addFilter(correlation)
        logging.root.addHandler(dd)
