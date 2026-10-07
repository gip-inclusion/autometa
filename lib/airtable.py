"""Client Airtable — lecture des tables et enregistrements (lecture seule)."""

import logging
import time
from typing import Any, Optional
from urllib.parse import quote

import httpx

from lib.api_signals import emit_api_signal
from web import config

logger = logging.getLogger(__name__)

BASE_URL = "https://api.airtable.com/v0"
DEFAULT_TIMEOUT = 30
# Garde-fou anti-emballement : 100 pages × 100 enregistrements avant arrêt + avertissement.
MAX_PAGES = 100
# Limite API : 5 requêtes par seconde et par base.
PAGE_INTERVAL_S = 0.2


class AirtableError(Exception):
    """Erreur d'appel à l'API Airtable."""


class AirtableClient:
    def __init__(self, token: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT):
        token = token or config.AIRTABLE_TOKEN
        if not token:
            raise AirtableError("AIRTABLE_TOKEN not set")
        self._session = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            transport=httpx.HTTPTransport(retries=2),
            timeout=httpx.Timeout(timeout, connect=10),
        )

    def close(self) -> None:
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        try:
            resp = self._session.get(path, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            hint = " (jeton sans accès à cette base, ou sans le scope data.records:read / schema.bases:read)"
            raise AirtableError(f"Airtable GET {path} -> HTTP {status}{hint if status == 403 else ''}") from e
        except httpx.RequestError as e:
            raise AirtableError(f"Airtable GET {path} -> {e}") from e
        emit_api_signal(source="airtable", instance="default", url=f"{BASE_URL}{path}", method=f"GET {path}")
        return data

    def list_tables(self, base_id: str) -> list[dict]:
        return self._get(f"/meta/bases/{base_id}/tables").get("tables", [])

    def list_records(
        self,
        base_id: str,
        table: str,
        view: Optional[str] = None,
        fields: Optional[list[str]] = None,
        formula: Optional[str] = None,
        max_pages: int = MAX_PAGES,
    ) -> list[dict]:
        """Enregistrements d'une table ou d'une vue, page par page (`offset`), plafonnés à `max_pages`."""
        params = {"pageSize": 100, "view": view, "fields[]": fields, "filterByFormula": formula}
        params = {k: v for k, v in params.items() if v}
        records: list[dict] = []
        for page in range(max_pages):
            if page:
                time.sleep(PAGE_INTERVAL_S)
            data = self._get(f"/{base_id}/{quote(table, safe='')}", params=params)
            records += data.get("records", [])
            if "offset" not in data:
                return records
            params = {**params, "offset": data["offset"]}
        logger.warning("Airtable: pagination plafonnée à %d pages pour %s/%s", max_pages, base_id, table)
        return records
