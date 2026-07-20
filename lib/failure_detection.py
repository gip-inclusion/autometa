"""Détection lexicale des aveux d'erreur de l'assistant et journalisation en base."""

import re
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, insert, text

from web.db import get_engine

SCHEMA = "dashboard_storage"

_metadata = MetaData(schema=SCHEMA)
conversation_failures = Table(
    "conversation_failures",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("conversation_id", String, nullable=False, index=True),
    Column("user_id", String),
    Column("title", String),
    Column("marker", String),
    Column("snippet", Text),
    Column("url", String),
    Column("detected_at", DateTime(timezone=True), nullable=False),
)

# Failure markers grouped by category
FAILURE_MARKERS = [
    # Erreurs
    "je me suis trompé",
    "erreur de ma part",
    "pardon",
    "mea culpa",
    # Corrections
    "correction :",
    "j'aurais dû",
    "je corrige",
    # Oublis
    "j'ai oublié",
    "oubli de ma part",
    "j'avais omis",
    # Excuses
    "désolé",
    "je m'excuse",
    "toutes mes excuses",
    # Échecs
    "n'a pas fonctionné",
    "a échoué",
    "impossible de",
    "je n'ai pas réussi",
]


def ensure_schema() -> None:
    eng = get_engine()
    with eng.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS " + SCHEMA))
    _metadata.create_all(eng)


def record_failure(
    conversation_id: str, title: str, marker: str, snippet: str, url: str, user_id: str | None = None
) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            insert(conversation_failures).values(
                conversation_id=conversation_id,
                user_id=user_id,
                title=title,
                marker=marker,
                snippet=snippet,
                url=url,
                detected_at=datetime.now(timezone.utc),
            )
        )


def find_failure_marker(text: str) -> str | None:
    text_lower = text.lower()
    for marker in FAILURE_MARKERS:
        if marker in text_lower:
            return marker
    return None


def extract_snippet(content: str, marker: str | None = None) -> str:
    content_lower = content.lower()
    markers_to_check = [marker] if marker else FAILURE_MARKERS

    for m in markers_to_check:
        pos = content_lower.find(m)
        if pos == -1:
            continue
        # Find sentence boundaries around the marker
        start = max(0, content.rfind(".", 0, pos) + 1)
        end = content.find(".", pos)
        if end == -1 or end - start > 200:
            end = min(len(content), pos + len(m) + 80)
        else:
            end += 1  # include the period
        snippet = content[start:end].strip()
        # Clean up markdown/whitespace
        snippet = re.sub(r"\s+", " ", snippet)
        if len(snippet) > 150:
            snippet = snippet[:147] + "..."
        return snippet
    return ""
