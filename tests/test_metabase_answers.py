"""
Answer verification tests for Metabase queries.

This test suite validates that given natural language questions,
the system can find correct answers using Metabase cards.

The tests use known-answer cases where we've verified the expected
result range by running the queries manually.

Run with: pytest tests/test_metabase_answers.py -v

To add new test cases:
1. Run the relevant card/query manually to get the current value
2. Define an appropriate range that accounts for data changes
3. Add to KNOWN_ANSWERS below
"""

import os
from dataclasses import dataclass
from typing import Optional

import pytest

from lib.query import get_metabase
from skills.metabase_query.scripts.cards_db import load_cards_db

_HAS_CREDENTIALS = bool(os.environ.get("METABASE_STATS_API_KEY"))
requires_credentials = pytest.mark.skipif(
    not _HAS_CREDENTIALS, reason="Integration test requires METABASE_STATS_API_KEY"
)


@dataclass
class ExpectedAnswer:
    """A known-answer test case."""

    question: str
    """Natural language question (for documentation)."""

    card_id: int
    """The card ID that answers this question."""

    expected_range: Optional[tuple[int, int]] = None
    """Expected numeric range (min, max) for the answer."""

    expected_contains: Optional[list[str]] = None
    """Expected strings that should appear in the result."""

    column_index: int = 0
    """Which column contains the answer (for multi-column results)."""

    row_index: int = 0
    """Which row contains the answer (for multi-row results)."""

    description: str = ""
    """Human-readable description of what this tests."""


KNOWN_ANSWERS = [
    ExpectedAnswer(
        question="Combien de candidats sont dans la file active ?",
        card_id=4413,
        expected_range=(50000, 150000),
        description="File active count - candidates waiting 30+ days without acceptance",
    ),
]


@pytest.fixture(scope="module")
def api():
    return get_metabase(instance="stats")


@pytest.mark.integration
@pytest.mark.parametrize(
    "case",
    KNOWN_ANSWERS,
    ids=[f"{c.card_id}_{c.question[:30]}" for c in KNOWN_ANSWERS],
)
def test_known_answers(api, case: ExpectedAnswer):
    """Verify card returns expected answer."""
    result = api.execute_card(case.card_id)

    assert result.row_count > 0, f"Card {case.card_id} returned no rows"

    if case.expected_range:
        value = result.rows[case.row_index][case.column_index]
        assert isinstance(value, (int, float)), f"Expected numeric value, got {type(value)}: {value}"
        min_val, max_val = case.expected_range
        assert min_val <= value <= max_val, (
            f"Value {value} outside expected range [{min_val}, {max_val}] for question: {case.question}"
        )

    if case.expected_contains:
        all_text = str(result.rows)
        for expected in case.expected_contains:
            assert expected in all_text, f"Expected '{expected}' not found in results for question: {case.question}"


@pytest.mark.integration
def test_card_discovery_search_file_active():
    db = load_cards_db()
    cards = db.search("file active")
    assert len(cards) > 0


@pytest.mark.integration
def test_card_discovery_search_candidatures():
    db = load_cards_db()
    cards = db.search("candidature")
    assert len(cards) > 0


@pytest.mark.integration
def test_card_discovery_search_by_table():
    db = load_cards_db()
    cards = db.by_table("candidatures_echelle_locale")
    assert len(cards) > 0


@pytest.mark.integration
def test_end_to_end_find_and_execute_card(api):
    db = load_cards_db()

    cards = db.search("candidature")
    assert len(cards) > 0

    card = cards[0]
    result = api.execute_card(card.id)

    assert result.row_count >= 0
    assert len(result.columns) > 0


@pytest.mark.integration
def test_end_to_end_card_sql_is_valid(api):
    """Cards with SQL can be used to understand the query."""
    db = load_cards_db()

    cards = db.all()
    cards_with_sql = [c for c in cards if c.sql_query]
    assert len(cards_with_sql) > 0, "Should have cards with SQL"

    card = cards_with_sql[0]
    assert card.sql_query, "Card should have SQL"

    sql_lower = card.sql_query.lower()
    assert any(kw in sql_lower for kw in ["select", "from", "where"]), "SQL should contain basic keywords"
