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
# Stems catch variants (token_auth, access_token, client_secret, …); exact set covers short unambiguous names.
_SECRET_KEY_STEMS = ("token", "secret", "password", "passwd", "apikey")
_SECRET_KEY_EXACT = frozenset({"api_key", "key", "pwd", "auth", "sig", "signature", "access_key"})


def _is_secret_param(key: str) -> bool:
    k = key.lower()
    return k in _SECRET_KEY_EXACT or any(stem in k for stem in _SECRET_KEY_STEMS)


def _mask_url(url: str) -> str:
    """Redact userinfo passwords (e.g. Postgres DSNs) and secret query params from a signal URL."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    netloc = parts.netloc
    if parts.password:
        host = parts.hostname or ""
        if ":" in host:  # IPv6 literal — urlsplit strips the brackets, put them back
            host = f"[{host}]"
        if parts.port:
            host = f"{host}:{parts.port}"
        netloc = f"{parts.username}:***@{host}" if parts.username else f"***@{host}"
    query = parts.query
    if query:
        pairs = parse_qsl(query, keep_blank_values=True)
        if any(_is_secret_param(k) for k, _ in pairs):
            query = urlencode([(k, "***" if _is_secret_param(k) else v) for k, v in pairs])
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
        # Why: sql is display content (agent-authored query text), intentionally not credential-masked.
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
