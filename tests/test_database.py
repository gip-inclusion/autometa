"""Tests for database module."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from web.database import (
    VALID_CONVERSATION_COLUMNS,
    VALID_REPORT_COLUMNS,
    build_update_clause,
    store,
)
from web.db import get_db
from web.models import Dashboard
from web.models import UsageEvent as UsageEventModel


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

    resp = client.post(f"/api/conversations/{conv.id}/cancel", headers={"X-Forwarded-Email": "test@test.com"})

    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    updated = store.get_conversation(conv.id, include_messages=False)
    assert not updated.needs_response


def test_cancel_clears_needs_response(client):
    conv = store.create_conversation(user_id="test@test.com")
    store.update_conversation(conv.id, needs_response=True)

    resp = client.post(f"/api/conversations/{conv.id}/cancel", headers={"X-Forwarded-Email": "test@test.com"})

    assert resp.status_code == 200
    updated = store.get_conversation(conv.id, include_messages=False)
    assert not updated.needs_response


def _load_usage_rows(conv_id):
    with get_db() as session:
        rows = session.scalars(select(UsageEventModel).where(UsageEventModel.conversation_id == conv_id)).all()
        return [
            {
                "kind": r.kind,
                "model": r.model,
                "cli_message_id": r.cli_message_id,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cache_creation_5m_tokens": r.cache_creation_5m_tokens,
                "cache_creation_1h_tokens": r.cache_creation_1h_tokens,
                "cache_read_tokens": r.cache_read_tokens,
                "web_search_requests": r.web_search_requests,
                "web_fetch_requests": r.web_fetch_requests,
            }
            for r in rows
        ]


def test_insert_usage_event_writes_row_and_bumps_cumulative(client):
    conv = store.create_conversation(user_id="test@test.com")
    store.insert_usage_event(
        conversation_id=conv.id,
        cli_message_id="msg_001",
        timestamp=datetime.now(timezone.utc),
        model="claude-sonnet-4-7",
        backend="cli",
        usage={
            "input_tokens": 10,
            "output_tokens": 20,
            "cache_creation_input_tokens": 30,
            "cache_read_input_tokens": 40,
            "service_tier": "standard",
            "server_tool_use": {"web_search_requests": 1, "web_fetch_requests": 2},
        },
    )

    rows = _load_usage_rows(conv.id)
    assert rows == [
        {
            "kind": "turn",
            "model": "claude-sonnet-4-7",
            "cli_message_id": "msg_001",
            "input_tokens": 10,
            "output_tokens": 20,
            "cache_creation_5m_tokens": 30,
            "cache_creation_1h_tokens": 0,
            "cache_read_tokens": 40,
            "web_search_requests": 1,
            "web_fetch_requests": 2,
        }
    ]
    loaded = store.get_conversation(conv.id, include_messages=False)
    assert loaded.usage_input_tokens == 10
    assert loaded.usage_output_tokens == 20
    assert loaded.usage_cache_creation_tokens == 30
    assert loaded.usage_cache_read_tokens == 40
    assert loaded.usage_backend == "cli"
    assert loaded.usage_extra == {"service_tier": "standard"}


def test_insert_usage_event_splits_ephemeral_cache(client):
    conv = store.create_conversation(user_id="test@test.com")
    store.insert_usage_event(
        conversation_id=conv.id,
        cli_message_id="msg_split",
        timestamp=datetime.now(timezone.utc),
        model="claude-opus-4-7",
        backend="cli",
        usage={
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 999,
            "cache_creation": {"ephemeral_5m_input_tokens": 400, "ephemeral_1h_input_tokens": 100},
        },
    )

    rows = _load_usage_rows(conv.id)
    assert rows[0]["cache_creation_5m_tokens"] == 400
    assert rows[0]["cache_creation_1h_tokens"] == 100
    loaded = store.get_conversation(conv.id, include_messages=False)
    assert loaded.usage_cache_creation_tokens == 500


def test_insert_usage_event_thinking_kind(client):
    conv = store.create_conversation(user_id="test@test.com")
    store.insert_usage_event(
        conversation_id=conv.id,
        cli_message_id=None,
        timestamp=datetime.now(timezone.utc),
        model="claude-opus-4-7",
        backend="cli",
        usage={"output_tokens": 1576, "service_tier": "standard"},
        kind="thinking",
    )

    rows = _load_usage_rows(conv.id)
    assert rows[0]["kind"] == "thinking"
    assert rows[0]["cli_message_id"] is None
    assert rows[0]["output_tokens"] == 1576
    assert rows[0]["input_tokens"] == 0
    assert rows[0]["cache_creation_5m_tokens"] == 0
    loaded = store.get_conversation(conv.id, include_messages=False)
    assert loaded.usage_output_tokens == 1576
    assert loaded.usage_input_tokens == 0


def _make_dashboard(slug, *, archived=False, author="alice@x", title=None):
    now = datetime.now(timezone.utc)
    with get_db() as session:
        session.add(
            Dashboard(
                slug=slug,
                title=title or slug,
                description="d",
                website="emplois",
                category="c",
                first_author_email=author,
                is_archived=archived,
                has_api_access=False,
                has_cron=False,
                has_persistence=False,
                created_at=now,
                updated_at=now,
            )
        )


def test_list_dashboards_excludes_archived_by_default(client):
    _make_dashboard("active-one")
    _make_dashboard("archived-one", archived=True)
    slugs = {d["slug"] for d in store.list_dashboards()}
    assert "active-one" in slugs
    assert "archived-one" not in slugs


def test_list_dashboards_include_archived(client):
    _make_dashboard("active-two")
    _make_dashboard("archived-two", archived=True)
    slugs = {d["slug"] for d in store.list_dashboards(include_archived=True)}
    assert {"active-two", "archived-two"} <= slugs


def test_list_archived_dashboards(client):
    _make_dashboard("active-three")
    _make_dashboard("archived-three", archived=True)
    slugs = {d["slug"] for d in store.list_archived_dashboards()}
    assert slugs == {"archived-three"}


def test_get_dashboard_returns_fields(client):
    _make_dashboard("detail-one", author="bob@x")
    d = store.get_dashboard("detail-one")
    assert d["slug"] == "detail-one"
    assert d["first_author_email"] == "bob@x"
    assert d["is_archived"] is False
    assert d["has_api_access"] is False
    assert d["url"] == "/interactive/detail-one/"


def test_get_dashboard_missing_returns_none(client):
    assert store.get_dashboard("does-not-exist") is None
