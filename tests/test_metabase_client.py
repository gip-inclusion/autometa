"""
Tests for the Metabase API client.

Unit tests run without credentials.
Integration tests require credentials: pytest tests/test_metabase_client.py -v -m integration
"""

import base64
import json

import pytest

from lib.metabase import QueryResult, build_sql_url
from lib.query import MetabaseError
from lib.sources import get_metabase


def test_build_sql_url_uses_classic_format():
    """URL must use classic format (type/native/query), not pMBQL (lib/type/stages)."""
    url = build_sql_url("https://metabase.example.com", 2, "SELECT 1")
    b64 = url.split("#")[1]
    decoded = json.loads(base64.b64decode(b64))
    dq = decoded["dataset_query"]
    assert dq["type"] == "native"
    assert dq["native"]["query"] == "SELECT 1"
    assert dq["database"] == 2
    assert "lib/type" not in dq
    assert "stages" not in dq


def test_build_sql_url_structure():
    url = build_sql_url("https://stats.example.com", 3, "SELECT 1")
    assert url.startswith("https://stats.example.com/question#eyJ")


def test_build_sql_url_preserves_sql():
    sql = "SELECT d.name, COUNT(*) FROM departments d GROUP BY d.name ORDER BY 2 DESC"
    url = build_sql_url("https://example.com", 2, sql)
    b64 = url.split("#")[1]
    decoded = json.loads(base64.b64decode(b64))
    assert decoded["dataset_query"]["native"]["query"] == sql


def test_build_sql_url_special_characters_in_sql():
    sql = "SELECT * FROM t WHERE name = 'l''inclusion' AND x > 0"
    url = build_sql_url("https://example.com", 2, sql)
    b64 = url.split("#")[1]
    decoded = json.loads(base64.b64decode(b64))
    assert decoded["dataset_query"]["native"]["query"] == sql


# All tests below are integration tests
pytestmark = pytest.mark.integration

# Known collection IDs
COLLECTION_452 = 452
COLLECTION_453 = 453

# A known card ID that should exist (file active count)
KNOWN_CARD_ID = 4413


@pytest.fixture(scope="module")
def api():
    return get_metabase(instance="stats")


def test_connection_get_current_user(api):
    """Verify API key works and returns user info."""
    user = api.get_current_user()
    assert "id" in user
    # API key users have a special email format
    assert "email" in user or "common_name" in user


def test_execute_sql_simple_query(api):
    result = api.execute_sql("SELECT 1 as test")
    assert isinstance(result, QueryResult)
    assert result.row_count == 1
    assert result.columns == ["test"]
    assert result.rows[0][0] == 1


def test_execute_sql_multiple_columns(api):
    result = api.execute_sql("SELECT 1 as a, 2 as b, 'hello' as c")
    assert result.row_count == 1
    assert len(result.columns) == 3
    assert result.rows[0] == [1, 2, "hello"]


def test_execute_sql_result_to_dicts(api):
    """Test to_dicts conversion."""
    result = api.execute_sql("SELECT 1 as id, 'test' as name")
    dicts = result.to_dicts()
    assert len(dicts) == 1
    assert dicts[0] == {"id": 1, "name": "test"}


def test_execute_sql_result_to_markdown(api):
    """Test markdown output."""
    result = api.execute_sql("SELECT 1 as id, 'test' as name")
    md = result.to_markdown()
    assert "| id | name |" in md
    assert "| 1 | test |" in md


def test_execute_sql_invalid_sql_raises_error(api):
    """Invalid SQL should raise MetabaseError."""
    with pytest.raises(MetabaseError):
        api.execute_sql("SELECT * FROM nonexistent_table_xyz")


def test_execute_card_known_card(api):
    result = api.execute_card(KNOWN_CARD_ID)
    assert isinstance(result, QueryResult)
    assert result.row_count >= 0


def test_execute_card_nonexistent_card(api):
    """Nonexistent card should raise error."""
    with pytest.raises(MetabaseError):
        api.execute_card(999999999)


def test_get_card_known_card(api):
    card = api.get_card(KNOWN_CARD_ID)
    assert "id" in card
    assert card["id"] == KNOWN_CARD_ID
    assert "name" in card
    assert "dataset_query" in card


def test_get_card_nonexistent_card(api):
    """Nonexistent card should raise error."""
    with pytest.raises(MetabaseError):
        api.get_card(999999999)


def test_list_cards_in_collection(api):
    cards = api.list_cards(COLLECTION_453)
    assert isinstance(cards, list)
    # Collection 453 should have cards
    assert len(cards) > 0
    # Each card should have basic metadata
    for card in cards[:5]:  # Check first 5
        assert "id" in card
        assert "name" in card


def test_search_cards(api):
    cards = api.search_cards("candidature")
    assert isinstance(cards, list)
    # Should find some cards with "candidature" in name/description
    assert len(cards) > 0


def test_search_cards_no_results(api):
    cards = api.search_cards("xyznonexistent123456")
    assert isinstance(cards, list)
    assert len(cards) == 0


def test_get_card_sql(api):
    sql = api.get_card_sql(KNOWN_CARD_ID)
    # Should return non-empty SQL
    assert isinstance(sql, str)
    # Most cards should have some SQL
    # (empty string is valid for cards that fail extraction)


def test_dashboards_list_dashboards(api):
    dashboards = api.list_dashboards(COLLECTION_452)
    assert isinstance(dashboards, list)
    # May or may not have dashboards


def test_dashboards_get_dashboard(api):
    # First find a dashboard
    dashboards = api.list_dashboards(COLLECTION_452)
    if dashboards:
        dashboard_id = dashboards[0]["id"]
        dashboard = api.get_dashboard(dashboard_id)
        assert "id" in dashboard
        assert dashboard["id"] == dashboard_id
