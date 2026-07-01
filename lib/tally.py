"""Client Tally (tally.so) — lecture de formulaires et de réponses (lecture seule, phase 1)."""

import logging
from typing import Any, Iterator, Optional

import httpx

from lib.api_signals import emit_api_signal
from web import config

logger = logging.getLogger(__name__)

BASE_URL = "https://api.tally.so"
DEFAULT_TIMEOUT = 30
# Garde-fou anti-emballement : 20 × 500 = 10 000 réponses avant arrêt + avertissement (limite API : 100 req/min).
MAX_SUBMISSION_PAGES = 20


class TallyError(Exception):
    """Erreur d'appel à l'API Tally."""


class TallyClient:
    def __init__(self, api_key: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT):
        self.api_key = api_key or config.TALLY_API_KEY
        if not self.api_key:
            raise TallyError("TALLY_API_KEY not set")
        self.timeout = timeout
        self._session = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            transport=httpx.HTTPTransport(retries=2),
        )

    def close(self) -> None:
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        try:
            resp = self._session.get(path, params=params, timeout=httpx.Timeout(self.timeout, connect=10))
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise TallyError(f"Tally GET {path} -> HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TallyError(f"Tally GET {path} -> {e}") from e
        emit_api_signal(source="tally", instance="default", url=f"{BASE_URL}{path}", method=f"GET {path}")
        return data

    def list_forms(self, page: int = 1, limit: int = 50) -> dict:
        return self._get("/forms", params={"page": page, "limit": limit})

    def get_form(self, form_id: str) -> dict:
        return self._get(f"/forms/{form_id}")

    def list_questions(self, form_id: str) -> dict:
        return self._get(f"/forms/{form_id}/questions")

    def list_submissions(
        self,
        form_id: str,
        *,
        filter: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        after_id: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> dict:
        params: dict[str, Any] = {"page": page, "limit": limit}
        if filter:
            params["filter"] = filter
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        if after_id:
            params["afterId"] = after_id
        return self._get(f"/forms/{form_id}/submissions", params=params)

    def iter_submissions(
        self,
        form_id: str,
        *,
        filter: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 500,
        max_pages: int = MAX_SUBMISSION_PAGES,
    ) -> Iterator[dict]:
        """Itère les réponses page par page (`hasMore`), plafonné à `max_pages`."""
        for page in range(1, max_pages + 1):
            data = self.list_submissions(
                form_id, filter=filter, start_date=start_date, end_date=end_date, page=page, limit=limit
            )
            yield from data.get("submissions", [])
            if not data.get("hasMore"):
                return
        logger.warning("Tally: pagination plafonnée à %d pages pour le formulaire %s", max_pages, form_id)


def list_workspaces(client: TallyClient) -> list[str]:
    """Workspaces visibles par la clé, dérivés des formulaires (l'API n'expose pas /workspaces)."""
    seen: dict[str, None] = {}
    for form in client.list_forms(limit=500).get("items", []):
        ws = form.get("workspaceId")
        if ws:
            seen.setdefault(ws, None)
    return list(seen)
