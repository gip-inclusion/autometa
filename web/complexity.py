"""Détection de conversations complexes pour suggérer l'aide d'un data."""

import json
import logging
import re

logger = logging.getLogger(__name__)

# Seuils métier (cf. indicateurs définis par l'équipe data)
QUERY_THRESHOLD = 50  # requêtes data sur la conversation
TURN_THRESHOLD = 40  # tours (messages utilisateur)
SOURCE_THRESHOLD = 3  # sources de données différentes
JOIN_TABLE_THRESHOLD = 5  # tables jointes dans une même requête

DATA_SKILLS = {
    "Skill: matomo_query",
    "Skill: metabase_query",
    "Skill: autometa_tables_db",
    "Skill: data_inclusion",
}

ALERT_MESSAGE = (
    "*Votre requête semble compliquée ! N'hésitez pas à faire appel à un data "
    "sur le canal tech-autometa en les taguant « @data ».*"
)
# Phrase stable servant à détecter une alerte déjà postée (anti-spam)
_ALERT_SENTINEL = "faire appel à un data"

_TABLE_PATTERNS = (
    r'FROM\s+"?(\w+)"?\."?(\w+)"?',
    r'FROM\s+"?(\w+)"?(?:\s|$|,)',
    r'JOIN\s+"?(\w+)"?\."?(\w+)"?',
    r'JOIN\s+"?(\w+)"?(?:\s|$)',
)
_TABLE_SKIP_WORDS = {"select", "case", "when", "then", "else", "end", "as", "on", "and", "or"}


def _is_data_category(category: str) -> bool:
    return category.startswith("API:") or category.startswith("Query:") or category in DATA_SKILLS


def _table_count(sql: str) -> int:
    tables = set()
    for pattern in _TABLE_PATTERNS:
        for match in re.findall(pattern, sql, re.IGNORECASE):
            table = [m for m in match if m][-1] if isinstance(match, tuple) else match
            if table and table.lower() not in _TABLE_SKIP_WORDS:
                tables.add(table.lower())
    return len(tables)


def evaluate(messages) -> list[str]:
    """Retourne la liste des indicateurs de complexité franchis (vide si simple)."""
    turns = sum(1 for m in messages if m.type == "user")
    queries = 0
    sources = set()
    max_join = 0

    for m in messages:
        if m.type == "tool_use":
            try:
                content = json.loads(m.content)
            except json.JSONDecodeError, TypeError:
                continue
            if _is_data_category(content.get("category", "")):
                queries += 1
            max_join = max(max_join, _table_count(json.dumps(content.get("input", ""))))
        elif m.type == "tool_result":
            try:
                content = json.loads(m.content)
            except json.JSONDecodeError, TypeError:
                continue
            if isinstance(content, dict):
                for call in content.get("api_calls", []):
                    sources.add((call.get("source"), call.get("instance")))

    reasons = []
    if queries > QUERY_THRESHOLD:
        reasons.append(f"requêtes={queries}")
    if turns > TURN_THRESHOLD:
        reasons.append(f"tours={turns}")
    if len(sources) > SOURCE_THRESHOLD:
        reasons.append(f"sources={len(sources)}")
    if max_join >= JOIN_TABLE_THRESHOLD:
        reasons.append(f"jointure={max_join}")
    return reasons


def already_alerted(messages) -> bool:
    return any(m.type == "assistant" and _ALERT_SENTINEL in m.content for m in messages)
