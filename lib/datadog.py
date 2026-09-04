"""Client Datadog Logs — lecture des logs applicatifs (lecture seule)."""

import logging
import threading
import time
from typing import Any, Iterator, Optional

import httpx

from lib.api_signals import emit_api_signal
from web import config

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60
PAGE_LIMIT = 1000
RETENTION_DAYS = 30

# Quota mesuré sur l'org (en-tête x-ratelimit-*) : 3 requêtes par fenêtre de 10 s, tous
# workers confondus. Se caler dessus coûte 10× moins cher que d'attendre les 429.
BURST, WINDOW_SEC = 3, 10.0

RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
MAX_ATTEMPTS = 6


class DatadogError(Exception):
    """Erreur d'appel à l'API Datadog."""


class RateLimiter:
    """Token bucket partagé : au plus `burst` requêtes par fenêtre glissante."""

    def __init__(self, burst: int = BURST, window: float = WINDOW_SEC):
        self.burst = burst
        self.window = window
        self._lock = threading.Lock()
        self._recent: list[float] = []

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                self._recent = [t for t in self._recent if now - t < self.window]
                if len(self._recent) < self.burst:
                    self._recent.append(now)
                    return
                wait = self.window - (now - self._recent[0]) + 0.05
            time.sleep(wait)


class DatadogClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        app_key: Optional[str] = None,
        site: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        limiter: Optional[RateLimiter] = None,
    ):
        self.api_key = api_key or config.DATADOG_API_KEY
        self.app_key = app_key or config.DATADOG_APP_KEY
        if not self.api_key or not self.app_key:
            raise DatadogError("DATADOG_API_KEY / DATADOG_APP_KEY not set")
        self.site = site or config.DATADOG_SITE
        self.timeout = timeout
        self.limiter = limiter or RateLimiter()
        self._session = httpx.Client(
            base_url=f"https://api.{self.site}/api/v2",
            headers={"DD-API-KEY": self.api_key, "DD-APPLICATION-KEY": self.app_key},
            transport=httpx.HTTPTransport(retries=2),
        )

    def close(self) -> None:
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _post(self, path: str, payload: dict) -> Any:
        emit_api_signal("datadog", self.site, f"https://api.{self.site}/api/v2{path}", method="POST")
        for attempt in range(MAX_ATTEMPTS):
            self.limiter.acquire()
            try:
                response = self._session.post(path, json=payload, timeout=self.timeout)
            except httpx.RequestError as exc:
                raise DatadogError(f"Datadog unreachable: {exc}") from exc
            if response.status_code in RETRYABLE_STATUS:
                logger.warning("Datadog %s on %s, retry %s", response.status_code, path, attempt + 1)
                time.sleep(WINDOW_SEC * (attempt + 1) / BURST)
                continue
            if response.status_code >= 400:
                raise DatadogError(f"HTTP {response.status_code}: {response.text[:200]}")
            return response.json()
        raise DatadogError(f"Datadog still rate-limited after {MAX_ATTEMPTS} attempts on {path}")

    def search(self, query: str, frm: str, to: str, limit: int = PAGE_LIMIT, cursor: Optional[str] = None) -> dict:
        page: dict[str, Any] = {"limit": limit}
        if cursor:
            page["cursor"] = cursor
        return self._post(
            "/logs/events/search",
            {"filter": {"query": query, "from": frm, "to": to}, "sort": "timestamp", "page": page},
        )

    def iter_events(self, query: str, frm: str, to: str, max_events: Optional[int] = None) -> Iterator[dict]:
        """Parcourt tous les événements d'une fenêtre, en suivant le curseur."""
        cursor, seen = None, 0
        while True:
            payload = self.search(query, frm, to, cursor=cursor)
            events = payload.get("data", [])
            for event in events:
                yield event
                seen += 1
                if max_events and seen >= max_events:
                    return
            cursor = payload.get("meta", {}).get("page", {}).get("after")
            if not cursor or not events:
                return

    def aggregate(
        self,
        query: str,
        frm: str,
        to: str,
        group_by: Optional[list[dict]] = None,
        compute: Optional[list[dict]] = None,
    ) -> list[dict]:
        payload: dict[str, Any] = {
            "filter": {"query": query, "from": frm, "to": to},
            "compute": compute or [{"aggregation": "count"}],
        }
        if group_by:
            payload["group_by"] = group_by
        return self._post("/logs/analytics/aggregate", payload)["data"]["buckets"]

    def count(self, query: str, frm: str, to: str, distinct: Optional[str] = None) -> dict:
        """Nombre d'événements, et cardinalité d'une facette quand `distinct` est donné."""
        compute: list[dict] = [{"aggregation": "count"}]
        if distinct:
            compute.append({"aggregation": "cardinality", "metric": distinct})
        buckets = self.aggregate(query, frm, to, compute=compute)
        if not buckets:
            return {"count": 0, "distinct": 0 if distinct else None}
        computes = buckets[0]["computes"]
        return {"count": computes.get("c0", 0), "distinct": computes.get("c1") if distinct else None}


def by_count(facet: str, limit: int = 50) -> dict:
    """Group_by trié par volume décroissant — sans `type: measure`, l'API rejette `aggregation` (400)."""
    return {"facet": facet, "limit": limit, "sort": {"aggregation": "count", "order": "desc", "type": "measure"}}


def day_windows(days: int, chunk: int = 1) -> list[tuple[str, str]]:
    """Découpe une fenêtre en tranches `now-Xd`, du plus ancien au plus récent."""
    if days > RETENTION_DAYS:
        raise DatadogError(f"Rétention Datadog : {RETENTION_DAYS} jours maximum (demandé : {days})")
    return [(f"now-{start}d", f"now-{max(start - chunk, 0)}d") for start in range(days, 0, -chunk)]
