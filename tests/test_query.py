"""
Tests for lib/query.py - the public query API with logging.

Run with: pytest tests/test_query.py -v
Integration tests (require .env): pytest tests/test_query.py -v -m integration
"""

import json
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# --- Structural tests ---


def test_query_module_imports():
    """Module imports without errors."""
    from lib import query
    assert hasattr(query, 'execute_query')
    assert hasattr(query, 'execute_metabase_query')
    assert hasattr(query, 'execute_matomo_query')
    assert hasattr(query, 'CallerType')
    assert hasattr(query, 'QueryResult')
    assert hasattr(query, 'get_query_stats')


def test_caller_type_enum():
    """CallerType enum has expected values."""
    from lib.query import CallerType
    assert CallerType.AGENT.value == "agent"
    assert CallerType.APP.value == "app"


def test_query_result_dataclass():
    """QueryResult dataclass has expected fields."""
    from lib.query import QueryResult
    result = QueryResult(success=True, data={"test": 1}, execution_time_ms=100)
    assert result.success is True
    assert result.data == {"test": 1}
    assert result.error is None
    assert result.execution_time_ms == 100


def test_sources_module_is_private():
    """lib._sources exists but is marked as private."""
    from lib import _sources
    # The module should have a docstring warning it's private
    assert "PRIVATE" in _sources.__doc__


def test_public_api_exports():
    """lib.query exports the public query functions."""
    from lib import query
    # These are the public API
    assert hasattr(query, 'execute_query')
    assert hasattr(query, 'execute_metabase_query')
    assert hasattr(query, 'execute_matomo_query')
    # get_matomo/get_metabase are internal (imported for use, not re-exported)
    # Note: They're technically accessible but not part of the documented API


# --- Unit tests (mocked) ---


class TestExecuteMetabaseQuery:
    """Tests for execute_metabase_query with mocked backend."""

    @pytest.fixture
    def mock_metabase_api(self):
        """Mock MetabaseAPI that returns a QueryResult-like object."""
        mock_result = MagicMock()
        mock_result.columns = ["id", "name"]
        mock_result.rows = [[1, "test"]]
        mock_result.row_count = 1

        mock_api = MagicMock()
        mock_api.execute_sql.return_value = mock_result
        mock_api.execute_card.return_value = mock_result
        return mock_api

    @patch('lib.query._log_query')
    @patch('lib.query.get_metabase')
    def test_executes_sql_query(self, mock_get_metabase, mock_log, mock_metabase_api):
        from lib.query import execute_metabase_query, CallerType

        mock_get_metabase.return_value = mock_metabase_api

        result = execute_metabase_query(
            instance="stats",
            caller=CallerType.AGENT,
            sql="SELECT 1",
            database_id=2,
        )

        assert result.success is True
        assert result.data["row_count"] == 1
        mock_metabase_api.execute_sql.assert_called_once()

    @patch('lib.query._log_query')
    @patch('lib.query.get_metabase')
    def test_executes_card_query(self, mock_get_metabase, mock_log, mock_metabase_api):
        from lib.query import execute_metabase_query, CallerType

        mock_get_metabase.return_value = mock_metabase_api

        result = execute_metabase_query(
            instance="stats",
            caller=CallerType.AGENT,
            card_id=123,
        )

        assert result.success is True
        mock_metabase_api.execute_card.assert_called_once_with(123, timeout=60)

    @patch('lib.query._log_query')
    @patch('lib.query.get_metabase')
    def test_logs_successful_query(self, mock_get_metabase, mock_log, mock_metabase_api):
        from lib.query import execute_metabase_query, CallerType

        mock_get_metabase.return_value = mock_metabase_api

        execute_metabase_query(
            instance="stats",
            caller=CallerType.AGENT,
            conversation_id="test-123",
            sql="SELECT 1",
            database_id=2,
        )

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args.kwargs
        assert call_kwargs["source"] == "metabase"
        assert call_kwargs["instance"] == "stats"
        assert call_kwargs["caller"] == CallerType.AGENT
        assert call_kwargs["conversation_id"] == "test-123"
        assert call_kwargs["success"] is True

    @patch('lib.query._log_query')
    @patch('lib.query.get_metabase')
    def test_logs_failed_query(self, mock_get_metabase, mock_log):
        from lib.query import execute_metabase_query, CallerType

        mock_get_metabase.side_effect = Exception("Connection failed")

        result = execute_metabase_query(
            instance="stats",
            caller=CallerType.AGENT,
            sql="SELECT 1",
            database_id=2,
        )

        assert result.success is False
        assert "Connection failed" in result.error
        mock_log.assert_called_once()
        assert mock_log.call_args.kwargs["success"] is False

    @patch('lib.query._log_query')
    @patch('lib.query.get_metabase')
    def test_requires_sql_or_card_id(self, mock_get_metabase, mock_log, mock_metabase_api):
        from lib.query import execute_metabase_query, CallerType

        mock_get_metabase.return_value = mock_metabase_api

        result = execute_metabase_query(
            instance="stats",
            caller=CallerType.AGENT,
            # Neither sql nor card_id provided
        )

        assert result.success is False
        assert "sql+database_id or card_id" in result.error


class TestExecuteMatomoQuery:
    """Tests for execute_matomo_query with mocked backend."""

    @pytest.fixture
    def mock_matomo_api(self):
        """Mock MatomoAPI."""
        mock_api = MagicMock()
        mock_api.request.return_value = {"nb_visits": 100}
        return mock_api

    @patch('lib.query._log_query')
    @patch('lib.query.get_matomo')
    def test_executes_matomo_query(self, mock_get_matomo, mock_log, mock_matomo_api):
        from lib.query import execute_matomo_query, CallerType

        mock_get_matomo.return_value = mock_matomo_api

        result = execute_matomo_query(
            instance="inclusion",
            caller=CallerType.AGENT,
            method="VisitsSummary.get",
            params={"idSite": 117, "period": "month", "date": "2025-12-01"},
        )

        assert result.success is True
        assert result.data == {"nb_visits": 100}
        mock_matomo_api.request.assert_called_once()

    @patch('lib.query._log_query')
    @patch('lib.query.get_matomo')
    def test_logs_with_method_as_query_type(self, mock_get_matomo, mock_log, mock_matomo_api):
        from lib.query import execute_matomo_query, CallerType

        mock_get_matomo.return_value = mock_matomo_api

        execute_matomo_query(
            instance="inclusion",
            caller=CallerType.AGENT,
            method="Events.getCategory",
            params={"idSite": 117},
        )

        call_kwargs = mock_log.call_args.kwargs
        assert call_kwargs["query_type"] == "Events.getCategory"

    @patch('lib.query._log_query')
    @patch('lib.query.get_matomo')
    def test_estimates_row_count_for_list_response(self, mock_get_matomo, mock_log):
        from lib.query import execute_matomo_query, CallerType

        mock_api = MagicMock()
        mock_api.request.return_value = [{"label": "a"}, {"label": "b"}, {"label": "c"}]
        mock_get_matomo.return_value = mock_api

        execute_matomo_query(
            instance="inclusion",
            caller=CallerType.AGENT,
            method="Events.getCategory",
            params={"idSite": 117},
        )

        call_kwargs = mock_log.call_args.kwargs
        assert call_kwargs["row_count"] == 3


class TestExecuteQuery:
    """Tests for the generic execute_query function."""

    @patch('lib.query.execute_metabase_query')
    def test_routes_to_metabase(self, mock_metabase):
        from lib.query import execute_query, CallerType, QueryResult

        mock_metabase.return_value = QueryResult(success=True, data={})

        execute_query(
            source="metabase",
            instance="stats",
            caller=CallerType.AGENT,
            sql="SELECT 1",
            database_id=2,
        )

        mock_metabase.assert_called_once()

    @patch('lib.query.execute_matomo_query')
    def test_routes_to_matomo(self, mock_matomo):
        from lib.query import execute_query, CallerType, QueryResult

        mock_matomo.return_value = QueryResult(success=True, data={})

        execute_query(
            source="matomo",
            instance="inclusion",
            caller=CallerType.AGENT,
            method="VisitsSummary.get",
            params={"idSite": 117},
        )

        mock_matomo.assert_called_once()

    def test_unknown_source_returns_error(self):
        from lib.query import execute_query, CallerType

        result = execute_query(
            source="unknown",
            instance="test",
            caller=CallerType.AGENT,
        )

        assert result.success is False
        assert "Unknown source" in result.error


class TestQueryLogging:
    """Tests for the actual logging to SQLite."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary audit database."""
        db_path = tmp_path / "test_audit.db"
        return db_path

    @patch('lib.query.AUDIT_DB_PATH')
    def test_log_query_creates_record(self, mock_path, temp_db):
        # Set up the mock to use our temp db
        mock_path.__str__ = lambda self: str(temp_db)
        mock_path.parent = temp_db.parent

        from lib.query import _log_query, _init_query_log_table, CallerType

        # Reinitialize with temp db
        with patch('lib.query.AUDIT_DB_PATH', temp_db):
            # Manually create the table
            conn = sqlite3.connect(str(temp_db))
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS query_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    instance TEXT NOT NULL,
                    caller TEXT NOT NULL,
                    conversation_id TEXT,
                    query_type TEXT,
                    query_details TEXT,
                    success INTEGER NOT NULL,
                    error TEXT,
                    execution_time_ms INTEGER,
                    row_count INTEGER
                );
            """)
            conn.commit()
            conn.close()

            # Now log a query
            _log_query(
                source="metabase",
                instance="stats",
                caller=CallerType.AGENT,
                conversation_id="test-conv-123",
                query_type="sql",
                query_details={"sql": "SELECT 1"},
                success=True,
                error=None,
                execution_time_ms=50,
                row_count=1,
            )

            # Verify
            conn = sqlite3.connect(str(temp_db))
            row = conn.execute("SELECT * FROM query_log ORDER BY id DESC LIMIT 1").fetchone()
            conn.close()

            assert row is not None
            # row[2] = source, row[3] = instance, row[4] = caller
            assert row[2] == "metabase"
            assert row[3] == "stats"
            assert row[4] == "agent"
            assert row[5] == "test-conv-123"


class TestGetQueryStats:
    """Tests for get_query_stats function."""

    @pytest.fixture
    def populated_db(self, tmp_path):
        """Create a temp db with some query logs."""
        db_path = tmp_path / "test_audit.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript("""
            CREATE TABLE query_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                instance TEXT NOT NULL,
                caller TEXT NOT NULL,
                conversation_id TEXT,
                query_type TEXT,
                query_details TEXT,
                success INTEGER NOT NULL,
                error TEXT,
                execution_time_ms INTEGER,
                row_count INTEGER
            );
        """)
        # Insert test data
        for i in range(5):
            conn.execute(
                """INSERT INTO query_log
                   (timestamp, source, instance, caller, success, execution_time_ms)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (datetime.utcnow().isoformat(), "metabase", "stats", "agent", 1, 100)
            )
        for i in range(3):
            conn.execute(
                """INSERT INTO query_log
                   (timestamp, source, instance, caller, success, execution_time_ms)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (datetime.utcnow().isoformat(), "matomo", "inclusion", "app", 1, 200)
            )
        # One failed query
        conn.execute(
            """INSERT INTO query_log
               (timestamp, source, instance, caller, success, error, execution_time_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (datetime.utcnow().isoformat(), "metabase", "stats", "agent", 0, "timeout", 5000)
        )
        conn.commit()
        conn.close()
        return db_path

    def test_returns_stats_dict(self, populated_db):
        with patch('lib.query.AUDIT_DB_PATH', populated_db):
            from lib.query import get_query_stats

            stats = get_query_stats()

            assert stats["total_queries"] == 9
            assert stats["successful_queries"] == 8
            assert stats["by_source"]["metabase"] == 6
            assert stats["by_source"]["matomo"] == 3
            assert stats["by_caller"]["agent"] == 6
            assert stats["by_caller"]["app"] == 3

    def test_filters_by_source(self, populated_db):
        with patch('lib.query.AUDIT_DB_PATH', populated_db):
            from lib.query import get_query_stats

            stats = get_query_stats(source="matomo")

            assert stats["total_queries"] == 3
            assert stats["by_source"] == {"matomo": 3}


# --- Integration tests ---


@pytest.mark.integration
class TestQueryIntegration:
    """Integration tests against real APIs (requires .env)."""

    def test_metabase_query_logs_to_db(self):
        """Real Metabase query is logged."""
        from lib.query import execute_metabase_query, CallerType, AUDIT_DB_PATH

        # Get count before
        conn = sqlite3.connect(str(AUDIT_DB_PATH))
        before = conn.execute("SELECT COUNT(*) FROM query_log").fetchone()[0]
        conn.close()

        # Execute query
        result = execute_metabase_query(
            instance="stats",
            caller=CallerType.AGENT,
            conversation_id="integration-test",
            sql="SELECT 1 as test",
            database_id=2,
        )

        # Get count after
        conn = sqlite3.connect(str(AUDIT_DB_PATH))
        after = conn.execute("SELECT COUNT(*) FROM query_log").fetchone()[0]
        last_row = conn.execute(
            "SELECT conversation_id FROM query_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()

        assert after == before + 1
        assert last_row[0] == "integration-test"

    def test_matomo_query_logs_to_db(self):
        """Real Matomo query is logged."""
        from lib.query import execute_matomo_query, CallerType, AUDIT_DB_PATH

        # Get count before
        conn = sqlite3.connect(str(AUDIT_DB_PATH))
        before = conn.execute("SELECT COUNT(*) FROM query_log").fetchone()[0]
        conn.close()

        # Execute query
        result = execute_matomo_query(
            instance="inclusion",
            caller=CallerType.AGENT,
            conversation_id="integration-test-matomo",
            method="SitesManager.getSitesWithAtLeastViewAccess",
            params={},
        )

        # Get count after
        conn = sqlite3.connect(str(AUDIT_DB_PATH))
        after = conn.execute("SELECT COUNT(*) FROM query_log").fetchone()[0]
        last_row = conn.execute(
            "SELECT conversation_id, query_type FROM query_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()

        assert after == before + 1
        assert last_row[0] == "integration-test-matomo"
        assert last_row[1] == "SitesManager.getSitesWithAtLeastViewAccess"
