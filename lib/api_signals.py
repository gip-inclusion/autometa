"""API call signals for observability.

When the agent runs scripts that call Matomo/Metabase APIs, we want to
capture those calls and display them in the UI sidebar with inspection links.

This module defines the signal protocol:
- API clients emit signals to stdout when making requests
- The backend parses these signals from tool_result content
- Signals are stored as metadata for the UI to display

Signal format:
    [AUTOMETA:API:{"source":"matomo","instance":"inclusion","method":"VisitsSummary.get","url":"https://..."}]

The bracketed format avoids conflicts with JSON output from the APIs.
"""

import json
import re
import sys
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from web import config

# Signal pattern for parsing — accepts both legacy MATOMETA and current AUTOMETA prefix
SIGNAL_PATTERN = re.compile(r"\[(?:AUTOMETA|MATOMETA):API:({.*?})\]")

# Query params whose value is a credential and must never reach tool output (stored in messages.content, shown in UI).
_SECRET_QUERY_KEYS = frozenset({"token_auth", "token", "api_key", "apikey", "key", "password", "secret"})


def _mask_url(url: str) -> str:
    """Redact userinfo passwords (e.g. Postgres DSNs) and secret query params from a signal URL."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    netloc = parts.netloc
    if parts.password:
        host = f"{parts.hostname or ''}:{parts.port}" if parts.port else (parts.hostname or "")
        netloc = f"{parts.username}:***@{host}" if parts.username else f"***@{host}"
    query = parts.query
    if query:
        pairs = parse_qsl(query, keep_blank_values=True)
        if any(k.lower() in _SECRET_QUERY_KEYS for k, _ in pairs):
            query = urlencode([(k, "***" if k.lower() in _SECRET_QUERY_KEYS else v) for k, v in pairs])
    return urlunsplit((parts.scheme, netloc, parts.path, query, parts.fragment))


def emit_api_signal(
    source: str,
    instance: str,
    url: str,
    method: Optional[str] = None,
    sql: Optional[str] = None,
    card_id: Optional[int] = None,
) -> None:
    # Why: the [AUTOMETA:API:...] line is parsed by the runner from agent subprocess stdout.
    # Outside that context (main process, cron jobs) it would land as plain text in Datadog
    # logs with no consumer. Skip emission when no agent conversation is active.
    if not config.agent_conversation_id():
        return

    signal = {
        "source": source,
        "instance": instance,
        "url": _mask_url(url),
    }

    if method:
        signal["method"] = method
    if sql:
        # Truncate SQL for display
        signal["sql"] = sql[:500] + "..." if len(sql) > 500 else sql
    if card_id is not None:
        signal["card_id"] = card_id

    print(f"[AUTOMETA:API:{json.dumps(signal)}]", file=sys.stdout, flush=True)


def parse_api_signals(content: str) -> list[dict]:
    signals = []
    for match in SIGNAL_PATTERN.finditer(content):
        try:
            signal = json.loads(match.group(1))
            signals.append(signal)
        except json.JSONDecodeError:
            pass  # malformed signal, skip
    return signals


def strip_api_signals(content: str) -> str:
    return SIGNAL_PATTERN.sub("", content).strip()
