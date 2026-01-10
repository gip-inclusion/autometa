"""Tests for database module."""

import pytest

from web.database import (
    _build_update_clause,
    VALID_CONVERSATION_COLUMNS,
    VALID_REPORT_COLUMNS,
)


class TestBuildUpdateClause:
    """Tests for the SQL injection prevention helper."""

    def test_builds_valid_clause_single_column(self):
        """Single valid column produces correct clause."""
        clause, values = _build_update_clause(
            {"title": "test"},
            VALID_CONVERSATION_COLUMNS
        )
        assert clause == "title = ?"
        assert values == ["test"]

    def test_builds_valid_clause_multiple_columns(self):
        """Multiple valid columns produce correct clause."""
        clause, values = _build_update_clause(
            {"title": "test", "status": "active"},
            VALID_CONVERSATION_COLUMNS
        )
        assert "title = ?" in clause
        assert "status = ?" in clause
        assert len(values) == 2
        assert "test" in values
        assert "active" in values

    def test_rejects_invalid_column(self):
        """Invalid column raises ValueError."""
        with pytest.raises(ValueError, match="Invalid column name: malicious"):
            _build_update_clause(
                {"malicious": "value"},
                VALID_CONVERSATION_COLUMNS
            )

    def test_rejects_sql_injection_attempt(self):
        """SQL injection attempt in column name raises ValueError."""
        with pytest.raises(ValueError):
            _build_update_clause(
                {"title; DROP TABLE users; --": "value"},
                VALID_CONVERSATION_COLUMNS
            )

    def test_rejects_mixed_valid_invalid_columns(self):
        """Mix of valid and invalid columns raises ValueError."""
        with pytest.raises(ValueError, match="Invalid column name"):
            _build_update_clause(
                {"title": "ok", "injected": "bad"},
                VALID_CONVERSATION_COLUMNS
            )

    def test_conversation_columns_are_valid(self):
        """All conversation columns in the frozenset work."""
        for col in VALID_CONVERSATION_COLUMNS:
            clause, values = _build_update_clause({col: "test"}, VALID_CONVERSATION_COLUMNS)
            assert f"{col} = ?" in clause

    def test_report_columns_are_valid(self):
        """All report columns in the frozenset work."""
        for col in VALID_REPORT_COLUMNS:
            clause, values = _build_update_clause({col: "test"}, VALID_REPORT_COLUMNS)
            assert f"{col} = ?" in clause

    def test_empty_updates_produces_empty_clause(self):
        """Empty dict produces empty clause."""
        clause, values = _build_update_clause({}, VALID_CONVERSATION_COLUMNS)
        assert clause == ""
        assert values == []
