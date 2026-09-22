"""Metabase API client."""

import base64
import json
import logging
import random
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from .api_signals import emit_api_signal

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
# Why: les crons ont un budget de 300s (`dashboards.cron_timeout`). On plafonne les retries à la
# moitié pour laisser au script de quoi finir, indépendamment du `timeout` passé par l'appelant.
RETRY_DEADLINE_S = 150.0
RETRY_BACKOFF_S = 2.0


def build_sql_url(base_url: str, database_id: int, sql: str) -> str:
    query_obj = {
        "dataset_query": {
            "type": "native",
            "native": {"query": sql, "template-tags": {}},
            "database": database_id,
        },
        "display": "table",
        "parameters": [],
        "visualization_settings": {},
        "type": "question",
    }
    encoded = base64.b64encode(json.dumps(query_obj).encode()).decode()
    return f"{base_url}/question#{encoded}"


@dataclass
class QueryResult:
    """Result from a Metabase query."""

    columns: list[str]
    rows: list[list[Any]]
    row_count: int

    def to_markdown(self, max_rows: int = 20) -> str:
        if self.row_count == 0:
            return "Aucun resultat trouve."

        lines = [f"Resultats ({self.row_count} lignes):", ""]

        # Header
        lines.append("| " + " | ".join(self.columns) + " |")
        lines.append("| " + " | ".join("---" for _ in self.columns) + " |")

        # Rows
        rows_to_show = min(max_rows, self.row_count)
        for i in range(rows_to_show):
            cells = [str(cell) if cell is not None else "" for cell in self.rows[i]]
            lines.append("| " + " | ".join(cells) + " |")

        if self.row_count > max_rows:
            lines.append(f"\n... et {self.row_count - max_rows} lignes supplementaires")

        return "\n".join(lines)

    def to_dicts(self) -> list[dict]:
        return [dict(zip(self.columns, row)) for row in self.rows]


class MetabaseError(Exception):
    pass


class MetabaseAPI:
    """
    Client for querying the Metabase API.

    Uses httpx.Client for connection pooling (reuses TCP+TLS across calls).
    Retries connection errors via httpx.HTTPTransport, and gateway statuses
    (502/503/504) or request errors with jittered linear backoff — ces échecs sont
    typiquement transitoires (Metabase saturé à ~06:00 quand tous les crons
    tapent l'API en même temps).

    Une tentative n'est lancée que si elle tient dans RETRY_DEADLINE_S : le
    coût total est donc borné quel que soit le `timeout` de l'appelant.
    """

    def __init__(
        self,
        url: str,
        api_key: str,
        database_id: Optional[int] = None,
        instance: str = "stats",
        caller: str = "agent",
    ):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.database_id = database_id if database_id is not None else 2
        self.instance = instance
        self.caller = caller

        transport = httpx.HTTPTransport(retries=2)
        self._session = httpx.Client(
            transport=transport,
            headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
            timeout=httpx.Timeout(60, connect=10),
        )

    def close(self) -> None:
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        timeout: int = 60,
        query_type: Optional[str] = None,
    ) -> Any:
        url = f"{self.url}{endpoint}"

        give_up_at = time.monotonic() + RETRY_DEADLINE_S

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                resp = self._session.request(
                    method, url, json=data if data else None, timeout=httpx.Timeout(timeout, connect=10)
                )
                resp.raise_for_status()
                return resp.json()

            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                # 502/503/504 = passerelle surchargée / timeout applicatif amont, transitoire → on retente.
                status = e.response.status_code if isinstance(e, httpx.HTTPStatusError) else None
                # Why: sans jitter, tous les crons de 06:00 qui prennent le même 504 retentent
                # à la même seconde et reforment la vague qui a saturé Metabase.
                backoff = RETRY_BACKOFF_S * attempt * random.uniform(0.5, 1.5)  # noqa: S311 — pas de la crypto
                # On ne démarre une tentative que si elle tient dans le budget : sinon le cron se fait
                # tuer en plein retry et l'erreur d'origine (le 504) est perdue au profit d'un timeout.
                if (
                    (status is None or status in (502, 503, 504))
                    and attempt < MAX_ATTEMPTS
                    and time.monotonic() + backoff + timeout <= give_up_at
                ):
                    logger.warning(
                        "Metabase %s %s -> %s (tentative %d), nouvel essai dans %.0fs",
                        method,
                        endpoint,
                        status or e,
                        attempt,
                        backoff,
                    )
                    time.sleep(backoff)
                    continue
                if status is not None:
                    raise MetabaseError(f"HTTP {status}: {e.response.text}") from e
                raise MetabaseError(str(e)) from e

    def _parse_result(self, data: dict) -> QueryResult:
        # Check for query errors (Metabase returns 202 with error in body)
        if data.get("error"):
            raise MetabaseError(data.get("error"))
        if data.get("status") == "failed":
            raise MetabaseError(data.get("error") or "Query failed")

        cols = data.get("data", {}).get("cols", [])
        rows = data.get("data", {}).get("rows", [])

        columns = [col.get("display_name") or col.get("name", f"col_{i}") for i, col in enumerate(cols)]

        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
        )

    # --- Core methods ---

    def execute_sql(self, sql: str, timeout: int = 60) -> QueryResult:
        data = {
            "database": self.database_id,
            "type": "native",
            "native": {"query": sql},
        }
        result_data = self._request("POST", "/api/dataset", data, timeout=timeout, query_type="sql")
        result = self._parse_result(result_data)

        # Emit signal for observability sidebar with shareable URL
        emit_api_signal(
            source="metabase",
            instance=self.instance,
            sql=sql,
            url=build_sql_url(self.url, self.database_id, sql),
        )

        return result

    def execute_card(self, card_id: int, timeout: int = 60) -> QueryResult:
        result_data = self._request("POST", f"/api/card/{card_id}/query", {}, timeout=timeout, query_type="card")
        result = self._parse_result(result_data)

        # Emit signal for observability sidebar
        emit_api_signal(
            source="metabase",
            instance=self.instance,
            card_id=card_id,
            url=f"{self.url}/question/{card_id}",
        )

        return result

    def get_card(self, card_id: int) -> dict:
        return self._request("GET", f"/api/card/{card_id}")

    # --- Discovery methods ---

    def list_cards(self, collection_id: int) -> list[dict]:
        result = self._request("GET", f"/api/collection/{collection_id}/items")
        items = result.get("data", [])
        return [item for item in items if item.get("model") == "card"]

    def search_cards(self, query: str, limit: int = 50) -> list[dict]:
        params = urllib.parse.urlencode({
            "q": query,
            "models": "card",
            "limit": limit,
        })
        result = self._request("GET", f"/api/search?{params}")
        return result.get("data", [])

    def get_card_sql(self, card_id: int) -> str:
        """
        Get the SQL query for a card.

        For native queries, returns the SQL directly.
        For GUI queries, executes the card to get compiled SQL.
        """
        card = self.get_card(card_id)
        dataset_query = card.get("dataset_query", {})

        # Native SQL query
        if dataset_query.get("type") == "native":
            return dataset_query.get("native", {}).get("query", "")

        # GUI query - need to execute to get compiled SQL
        try:
            result = self._request("POST", f"/api/card/{card_id}/query", {})
            native_form = result.get("data", {}).get("native_form", {})
            return native_form.get("query", "")
        except MetabaseError:
            return ""

    # --- Dashboard methods ---

    def list_models(self) -> list[dict]:
        """List all model-type cards (Metabase datasets)."""
        return self._request("GET", "/api/card?f=dataset", timeout=30)

    def get_dashboard(self, dashboard_id: int) -> dict:
        return self._request("GET", f"/api/dashboard/{dashboard_id}")

    def list_dashboards(self, collection_id: int) -> list[dict]:
        result = self._request("GET", f"/api/collection/{collection_id}/items")
        items = result.get("data", [])
        return [item for item in items if item.get("model") == "dashboard"]

    # --- User info ---

    def get_current_user(self) -> dict:
        return self._request("GET", "/api/user/current")
