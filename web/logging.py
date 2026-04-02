"""Logging setup with optional Datadog forwarding.

When DATADOG_API_KEY is set, logs are sent to the Datadog HTTP intake in
addition to the console.
"""

import atexit
import json
import logging
import queue
import threading

import httpx

from . import config

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class DatadogHandler(logging.Handler):
    """Async-buffered handler that sends logs to Datadog HTTP intake."""

    def __init__(self, api_key: str, *, batch_size: int = 50, flush_interval: float = 5.0):
        super().__init__()
        self._api_key = api_key
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._queue: queue.Queue[dict] = queue.Queue(maxsize=10_000)
        self._shutdown = threading.Event()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        atexit.register(self.close)

    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "message": self.format(record),
            "ddsource": "python",
            "service": "autometa",
            "hostname": config.HOST,
            "ddtags": "env:prod",
            "level": record.levelname,
            "logger": {"name": record.name},
        }
        try:
            self._queue.put_nowait(entry)
        except queue.Full:
            pass

    def _worker(self) -> None:
        client = httpx.Client(timeout=10)
        while not self._shutdown.is_set():
            batch = self._drain(self._batch_size)
            if not batch:
                self._shutdown.wait(self._flush_interval)
                continue
            self._send(client, batch)
        # Final flush
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
        # Why: background thread must not crash on transient network errors.
        except Exception:
            pass

    def close(self) -> None:
        self._shutdown.set()
        self._thread.join(timeout=5)
        super().close()


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger with optional Datadog handler."""
    formatter = logging.Formatter(_LOG_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    logging.root.handlers.clear()
    logging.root.addHandler(console)
    logging.root.setLevel(level)

    if config.DATADOG_API_KEY:
        dd = DatadogHandler(config.DATADOG_API_KEY)
        dd.setFormatter(formatter)
        logging.root.addHandler(dd)
