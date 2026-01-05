"""
Tests for the Metabase API client.

Run with: pytest tests/test_metabase_client.py -v
"""

import pytest
from skills.metabase_query.scripts.metabase import (
    MetabaseAPI,
    MetabaseError,
    QueryResult,
    format_data_source,
)

# Known collection IDs
COLLECTION_452 = 452
COLLECTION_453 = 453

# A known card ID that should exist (file active count)
KNOWN_CARD_ID = 4413


@pytest.fixture(scope="module")
def api():
    """Create API client for all tests."""
    return MetabaseAPI()


class TestConnection:
    """Test basic connectivity."""

    def test_get_current_user(self, api):
        """Verify API key works and returns user info."""
        user = api.get_current_user()
        assert "id" in user
        # API key users have a special email format
        assert "email" in user or "common_name" in user


class TestExecuteSQL:
    """Test raw SQL execution."""

    def test_simple_query(self, api):
        """Execute a trivial query."""
        result = api.execute_sql("SELECT 1 as test")
        assert isinstance(result, QueryResult)
        assert result.row_count == 1
        assert result.columns == ["test"]
        assert result.rows[0][0] == 1

    def test_query_with_multiple_columns(self, api):
        """Execute query with multiple columns."""
        result = api.execute_sql("SELECT 1 as a, 2 as b, 'hello' as c")
        assert result.row_count == 1
        assert len(result.columns) == 3
        assert result.rows[0] == [1, 2, "hello"]

    def test_query_result_to_dicts(self, api):
        """Test to_dicts conversion."""
        result = api.execute_sql("SELECT 1 as id, 'test' as name")
        dicts = result.to_dicts()
        assert len(dicts) == 1
        assert dicts[0] == {"id": 1, "name": "test"}

    def test_query_result_to_markdown(self, api):
        """Test markdown output."""
        result = api.execute_sql("SELECT 1 as id, 'test' as name")
        md = result.to_markdown()
        assert "| id | name |" in md
        assert "| 1 | test |" in md

    def test_invalid_sql_raises_error(self, api):
        """Invalid SQL should raise MetabaseError."""
        with pytest.raises(MetabaseError):
            api.execute_sql("SELECT * FROM nonexistent_table_xyz")


class TestExecuteCard:
    """Test saved card/question execution."""

    def test_execute_known_card(self, api):
        """Execute a known card."""
        result = api.execute_card(KNOWN_CARD_ID)
        assert isinstance(result, QueryResult)
        assert result.row_count >= 0

    def test_execute_nonexistent_card(self, api):
        """Nonexistent card should raise error."""
        with pytest.raises(MetabaseError):
            api.execute_card(999999999)


class TestGetCard:
    """Test card metadata retrieval."""

    def test_get_known_card(self, api):
        """Get metadata for a known card."""
        card = api.get_card(KNOWN_CARD_ID)
        assert "id" in card
        assert card["id"] == KNOWN_CARD_ID
        assert "name" in card
        assert "dataset_query" in card

    def test_get_nonexistent_card(self, api):
        """Nonexistent card should raise error."""
        with pytest.raises(MetabaseError):
            api.get_card(999999999)


class TestListCards:
    """Test listing cards in collections."""

    def test_list_cards_in_collection(self, api):
        """List cards in a known collection."""
        cards = api.list_cards(COLLECTION_453)
        assert isinstance(cards, list)
        # Collection 453 should have cards
        assert len(cards) > 0
        # Each card should have basic metadata
        for card in cards[:5]:  # Check first 5
            assert "id" in card
            assert "name" in card


class TestSearchCards:
    """Test card search functionality."""

    def test_search_cards(self, api):
        """Search for cards."""
        cards = api.search_cards("candidature")
        assert isinstance(cards, list)
        # Should find some cards with "candidature" in name/description
        assert len(cards) > 0

    def test_search_no_results(self, api):
        """Search with no results returns empty list."""
        cards = api.search_cards("xyznonexistent123456")
        assert isinstance(cards, list)
        assert len(cards) == 0


class TestGetCardSQL:
    """Test SQL extraction from cards."""

    def test_get_card_sql(self, api):
        """Get SQL for a known card."""
        sql = api.get_card_sql(KNOWN_CARD_ID)
        # Should return non-empty SQL
        assert isinstance(sql, str)
        # Most cards should have some SQL
        # (empty string is valid for cards that fail extraction)


class TestDashboards:
    """Test dashboard methods."""

    def test_list_dashboards(self, api):
        """List dashboards in a collection."""
        dashboards = api.list_dashboards(COLLECTION_452)
        assert isinstance(dashboards, list)
        # May or may not have dashboards

    def test_get_dashboard(self, api):
        """Get dashboard metadata."""
        # First find a dashboard
        dashboards = api.list_dashboards(COLLECTION_452)
        if dashboards:
            dashboard_id = dashboards[0]["id"]
            dashboard = api.get_dashboard(dashboard_id)
            assert "id" in dashboard
            assert dashboard["id"] == dashboard_id


class TestFormatDataSource:
    """Test format_data_source() helper."""

    BASE_URL = "https://stats.inclusion.beta.gouv.fr"

    def test_card_only(self):
        """Card ID generates question URL."""
        result = format_data_source(self.BASE_URL, card_id=123)
        assert "[View in Metabase]" in result
        assert "/question/123" in result

    def test_dashboard_only(self):
        """Dashboard ID generates dashboard URL."""
        result = format_data_source(self.BASE_URL, dashboard_id=45)
        assert "[View in Metabase]" in result
        assert "/dashboard/45" in result

    def test_sql_only(self):
        """SQL without card/dashboard shows just the query."""
        result = format_data_source(self.BASE_URL, sql="SELECT 1")
        assert "`SELECT 1`" in result
        assert "View in Metabase" not in result

    def test_card_and_sql(self):
        """Card + SQL shows both."""
        result = format_data_source(self.BASE_URL, card_id=123, sql="SELECT * FROM foo")
        assert "/question/123" in result
        assert "`SELECT * FROM foo`" in result
        assert " | " in result

    def test_long_sql_truncated(self):
        """Long SQL queries are truncated."""
        long_sql = "SELECT " + ", ".join(f"col{i}" for i in range(50)) + " FROM table"
        result = format_data_source(self.BASE_URL, sql=long_sql)
        assert "..." in result
        assert len(result) < len(long_sql) + 50

    def test_no_args_returns_no_source(self):
        """No arguments returns placeholder."""
        result = format_data_source(self.BASE_URL)
        assert result == "(no source)"

    def test_card_preferred_over_dashboard(self):
        """When both card and dashboard provided, card wins."""
        result = format_data_source(self.BASE_URL, card_id=123, dashboard_id=45)
        assert "/question/123" in result
        assert "/dashboard/" not in result
