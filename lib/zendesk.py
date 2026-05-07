"""Zendesk API client — support Emplois de l'Inclusion."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30
_RATE_LIMIT_PER_MIN = 700
_MIN_DELAY = 60.0 / _RATE_LIMIT_PER_MIN


@dataclass
class ZendeskComment:
    id: int
    ticket_id: int
    body: str
    html_body: str
    public: bool
    author_id: int
    created_at: str
    author_role: Optional[str] = None


@dataclass
class ZendeskTicket:
    id: int
    subject: str
    status: str
    created_at: str
    updated_at: str
    requester_id: int
    assignee_id: Optional[int]
    tags: list[str] = field(default_factory=list)


@dataclass
class ZendeskError(Exception):
    status_code: int
    message: str

    def __str__(self) -> str:
        return f"Zendesk {self.status_code}: {self.message}"


class ZendeskAPI:
    """Read-only Zendesk REST API client with built-in rate limiting."""

    def __init__(self, subdomain: str, email: str, token: str) -> None:
        self.base_url = f"https://{subdomain}.zendesk.com/api/v2"
        self._client = httpx.Client(
            auth=(f"{email}/token", token),
            headers={"Accept": "application/json"},
            timeout=_DEFAULT_TIMEOUT,
        )
        self._last_call: float = 0.0

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        elapsed = time.monotonic() - self._last_call
        if elapsed < _MIN_DELAY:
            time.sleep(_MIN_DELAY - elapsed)
        url = f"{self.base_url}/{path.lstrip('/')}"
        response = self._client.get(url, params=params or {})
        self._last_call = time.monotonic()
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            logger.warning("Zendesk rate-limited, sleeping %ss", retry_after)
            time.sleep(retry_after)
            return self._get(path, params)
        if not response.is_success:
            raise ZendeskError(response.status_code, response.text[:200])
        return response.json()

    def get_ticket(self, ticket_id: int) -> ZendeskTicket:
        data = self._get(f"tickets/{ticket_id}")["ticket"]
        return ZendeskTicket(
            id=data["id"],
            subject=data.get("subject") or "",
            status=data["status"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            requester_id=data["requester_id"],
            assignee_id=data.get("assignee_id"),
            tags=data.get("tags", []),
        )

    def get_ticket_comments(self, ticket_id: int) -> list[ZendeskComment]:
        """Return all comments for a ticket, oldest first."""
        data = self._get(f"tickets/{ticket_id}/comments", {"sort_order": "asc"})
        sideloaded_users: dict[int, str] = {}
        for u in data.get("users", []):
            sideloaded_users[u["id"]] = u.get("role", "end-user")
        comments = []
        for c in data.get("comments", []):
            author_id = c["author_id"]
            comments.append(
                ZendeskComment(
                    id=c["id"],
                    ticket_id=ticket_id,
                    body=c.get("plain_body") or c.get("body") or "",
                    html_body=c.get("html_body") or "",
                    public=c.get("public", True),
                    author_id=author_id,
                    created_at=c["created_at"],
                    author_role=sideloaded_users.get(author_id),
                )
            )
        return comments

    def first_user_reply(self, ticket_id: int) -> Optional[ZendeskComment]:
        """First end-user comment after the first agent comment (the 'clarification')."""
        comments = self.get_ticket_comments(ticket_id)
        agent_seen = False
        for c in comments:
            if c.author_role in ("agent", "admin"):
                agent_seen = True
            elif agent_seen and c.author_role == "end-user":
                return c
        return None

    def iter_tickets(
        self,
        ticket_ids: list[int],
        with_comments: bool = False,
    ) -> Iterator[dict[str, Any]]:
        """Yield dicts {ticket, comments} for each ticket_id. Shows progress."""
        total = len(ticket_ids)
        for i, tid in enumerate(ticket_ids, 1):
            result: dict[str, Any] = {"ticket_id": tid}
            try:
                if with_comments:
                    result["comments"] = self.get_ticket_comments(tid)
                else:
                    result["ticket"] = self.get_ticket(tid)
            except ZendeskError as exc:
                logger.warning("Ticket %s skipped: %s", tid, exc)
                result["error"] = str(exc)
            yield result
            if i % 500 == 0:
                logger.info("Zendesk: %d/%d tickets traités", i, total)

    def check_auth(self) -> dict[str, str]:
        """Verify credentials. Returns current user info."""
        return self._get("users/me")["user"]
