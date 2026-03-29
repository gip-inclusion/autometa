"""Tests for database module."""

import pytest

from web.database import (
    VALID_CONVERSATION_COLUMNS,
    VALID_REPORT_COLUMNS,
    build_update_clause,
    store,
)


def test_build_update_clause_builds_valid_clause_single_column():
    clause, values = build_update_clause({"title": "test"}, VALID_CONVERSATION_COLUMNS)
    assert clause == "title = %s"
    assert values == ["test"]


def test_build_update_clause_builds_valid_clause_multiple_columns():
    clause, values = build_update_clause({"title": "test", "status": "active"}, VALID_CONVERSATION_COLUMNS)
    assert "title = %s" in clause
    assert "status = %s" in clause
    assert len(values) == 2
    assert "test" in values
    assert "active" in values


def test_build_update_clause_rejects_invalid_column():
    with pytest.raises(ValueError, match="Invalid column name: malicious"):
        build_update_clause({"malicious": "value"}, VALID_CONVERSATION_COLUMNS)


def test_build_update_clause_rejects_sql_injection_attempt():
    with pytest.raises(ValueError):
        build_update_clause({"title; DROP TABLE users; --": "value"}, VALID_CONVERSATION_COLUMNS)


def test_build_update_clause_rejects_mixed_valid_invalid_columns():
    with pytest.raises(ValueError, match="Invalid column name"):
        build_update_clause({"title": "ok", "injected": "bad"}, VALID_CONVERSATION_COLUMNS)


def test_build_update_clause_conversation_columns_are_valid():
    for col in VALID_CONVERSATION_COLUMNS:
        clause, values = build_update_clause({col: "test"}, VALID_CONVERSATION_COLUMNS)
        assert f"{col} = %s" in clause


def test_build_update_clause_report_columns_are_valid():
    for col in VALID_REPORT_COLUMNS:
        clause, values = build_update_clause({col: "test"}, VALID_REPORT_COLUMNS)
        assert f"{col} = %s" in clause


def test_build_update_clause_empty_updates_produces_empty_clause():
    clause, values = build_update_clause({}, VALID_CONVERSATION_COLUMNS)
    assert clause == ""
    assert values == []


def test_clear_all_needs_response_clears_stuck_conversations(client):
    conv = store.create_conversation(user_id="test@test.com")
    store.update_conversation(conv.id, needs_response=True)

    cleared_ids = store.clear_all_needs_response()

    assert cleared_ids == [conv.id]
    updated = store.get_conversation(conv.id, include_messages=False)
    assert not updated.needs_response


def test_clear_all_needs_response_noop_when_nothing_stuck(client):
    store.create_conversation(user_id="test@test.com")
    assert store.clear_all_needs_response() == []


def test_cancel_unstick_zombie_conversation(client):
    conv = store.create_conversation(user_id="test@test.com")
    store.update_conversation(conv.id, needs_response=True)

    resp = client.post(f"/api/conversations/{conv.id}/cancel")

    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    updated = store.get_conversation(conv.id, include_messages=False)
    assert not updated.needs_response


def test_cancel_clears_needs_response(client):
    conv = store.create_conversation(user_id="test@test.com")
    store.update_conversation(conv.id, needs_response=True)

    resp = client.post(f"/api/conversations/{conv.id}/cancel")

    assert resp.status_code == 200
    updated = store.get_conversation(conv.id, include_messages=False)
    assert not updated.needs_response
