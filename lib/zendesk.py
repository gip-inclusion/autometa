"""Zendesk API client — support Emplois de l'Inclusion."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

import httpx

from .api_signals import emit_api_signal

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30
# Zendesk Suite Professional plan limit. Lower tiers (Team: 200, Growth: 400)
# will hit 429 more often — handled by the bounded retry loop below.
_RATE_LIMIT_PER_MIN = 700
_MIN_DELAY = 60.0 / _RATE_LIMIT_PER_MIN
_MAX_429_RETRIES = 3


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
class TicketResult:
    ticket_id: int
    ticket: Optional[ZendeskTicket] = None
    comments: Optional[list[ZendeskComment]] = None
    error: Optional[str] = None


class ZendeskError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"Zendesk {status_code}: {message}")


def _parse_retry_after(value: Optional[str], default: int = 60) -> int:
    if not value:
        return default
    try:
        return max(0, int(value))
    except ValueError:
        return default


class ZendeskAPI:
    """Read-only Zendesk REST API client with built-in rate limiting."""

    def __init__(
        self,
        subdomain: str,
        email: str,
        token: str,
        instance: str = "emplois",
    ) -> None:
        self.base_url = f"https://{subdomain}.zendesk.com/api/v2"
        self.instance = instance
        self._client = httpx.Client(
            transport=httpx.HTTPTransport(retries=2),
            auth=(f"{email}/token", token),
            headers={"Accept": "application/json"},
            timeout=_DEFAULT_TIMEOUT,
        )
        self._last_call: float = 0.0

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        response: Optional[httpx.Response] = None
        for attempt in range(_MAX_429_RETRIES + 1):
            elapsed = time.monotonic() - self._last_call
            if elapsed < _MIN_DELAY:
                time.sleep(_MIN_DELAY - elapsed)
            response = self._client.get(url, params=params or {})
            self._last_call = time.monotonic()
            if response.status_code != 429:
                break
            if attempt == _MAX_429_RETRIES:
                raise ZendeskError(429, f"rate limited after {_MAX_429_RETRIES} retries")
            retry_after = _parse_retry_after(response.headers.get("Retry-After"))
            logger.warning("Zendesk rate-limited, sleeping %ss", retry_after)
            time.sleep(retry_after)
        if not response.is_success:
            raise ZendeskError(response.status_code, response.text[:200])
        emit_api_signal(source="zendesk", instance=self.instance, url=str(response.url))
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
        """Return all comments for a ticket, oldest first (first page only — see SKILL.md)."""
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
    ) -> Iterator[TicketResult]:
        """Yield TicketResult per id; logs progress every 500. with_comments=True doubles API calls."""
        total = len(ticket_ids)
        for i, tid in enumerate(ticket_ids, 1):
            result = TicketResult(ticket_id=tid)
            try:
                result.ticket = self.get_ticket(tid)
                if with_comments:
                    result.comments = self.get_ticket_comments(tid)
            except ZendeskError as exc:
                logger.warning("Ticket %s skipped: %s", tid, exc)
                result.error = str(exc)
            yield result
            if i % 500 == 0:
                logger.info("Zendesk: %d/%d tickets traités", i, total)

    def check_auth(self) -> dict[str, str]:
        """Verify credentials. Returns current user info."""
        return self._get("users/me")["user"]
