"""Tests for usage tracking across backends."""

import pytest
from sqlalchemy import text

from web.agents.base import AgentMessage
from web.agents.cli import CLIBackend
from web.database import Conversation, ConversationStore, get_db
from web.schema import init_db


@pytest.mark.parametrize(
    "field,default",
    [
        ("usage_input_tokens", 0),
        ("usage_output_tokens", 0),
        ("usage_cache_creation_tokens", 0),
        ("usage_cache_read_tokens", 0),
        ("usage_backend", None),
        ("usage_extra", None),
    ],
)
def test_conversation_usage_field_defaults(field, default):
    conv = Conversation()
    assert getattr(conv, field) == default


def test_conversation_usage_fields_to_dict_includes_usage_fields():

    conv = Conversation(
        usage_input_tokens=100,
        usage_output_tokens=50,
        usage_cache_creation_tokens=20,
        usage_cache_read_tokens=80,
        usage_backend="cli",
        usage_extra={"service_tier": "standard"},
    )
    data = conv.to_dict()
    assert data["usage_input_tokens"] == 100
    assert data["usage_output_tokens"] == 50
    assert data["usage_cache_creation_tokens"] == 20
    assert data["usage_cache_read_tokens"] == 80
    assert data["usage_backend"] == "cli"
    assert data["usage_extra"] == {"service_tier": "standard"}


@pytest.fixture
def db_setup():

    init_db()
    yield

    with get_db() as session:
        session.execute(
            text("""
            TRUNCATE TABLE messages, conversation_tags, report_tags,
                uploaded_files, cron_runs, pinned_items, pm_commands,
                pm_heartbeat, reports, conversations, tags, schema_version
                CASCADE;
        """)
        )


def test_database_usage_columns_conversations_table_has_usage_columns(db_setup):

    with get_db() as session:
        rows = (
            session
            .execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = :tbl"),
                {"tbl": "conversations"},
            )
            .mappings()
            .all()
        )
        columns = {row["column_name"] for row in rows}
        assert "usage_input_tokens" in columns
        assert "usage_output_tokens" in columns
        assert "usage_cache_creation_tokens" in columns
        assert "usage_cache_read_tokens" in columns
        assert "usage_backend" in columns
        assert "usage_extra" in columns


def test_database_usage_columns_create_conversation_stores_zero_usage(db_setup):

    store = ConversationStore()
    conv = store.create_conversation(user_id="test")

    loaded = store.get_conversation(conv.id)
    assert loaded.usage_input_tokens == 0
    assert loaded.usage_output_tokens == 0
    assert loaded.usage_cache_creation_tokens == 0
    assert loaded.usage_cache_read_tokens == 0
    assert loaded.usage_backend is None
    assert loaded.usage_extra is None


def test_database_usage_columns_update_conversation_usage(db_setup):

    store = ConversationStore()
    conv = store.create_conversation(user_id="test")

    # Update usage
    store.update_conversation_usage(
        conv.id,
        input_tokens=1500,
        output_tokens=800,
        cache_creation_tokens=100,
        cache_read_tokens=500,
        backend="cli",
        extra={"service_tier": "priority", "web_search_requests": 2},
    )

    loaded = store.get_conversation(conv.id)
    assert loaded.usage_input_tokens == 1500
    assert loaded.usage_output_tokens == 800
    assert loaded.usage_cache_creation_tokens == 100
    assert loaded.usage_cache_read_tokens == 500
    assert loaded.usage_backend == "cli"
    assert loaded.usage_extra == {"service_tier": "priority", "web_search_requests": 2}


def test_database_usage_columns_accumulate_usage(db_setup):

    store = ConversationStore()
    conv = store.create_conversation(user_id="test")

    # First exchange
    store.accumulate_usage(
        conv.id,
        input_tokens=100,
        output_tokens=50,
        cache_creation_tokens=10,
        cache_read_tokens=0,
        backend="cli",
    )
    loaded = store.get_conversation(conv.id)
    assert loaded.usage_input_tokens == 100
    assert loaded.usage_output_tokens == 50
    assert loaded.usage_cache_creation_tokens == 10
    assert loaded.usage_cache_read_tokens == 0
    assert loaded.usage_backend == "cli"

    # Second exchange
    store.accumulate_usage(
        conv.id,
        input_tokens=200,
        output_tokens=150,
        cache_creation_tokens=0,
        cache_read_tokens=80,
    )
    loaded = store.get_conversation(conv.id)
    assert loaded.usage_input_tokens == 300
    assert loaded.usage_output_tokens == 200
    assert loaded.usage_cache_creation_tokens == 10
    assert loaded.usage_cache_read_tokens == 80
    # Backend should persist from first call
    assert loaded.usage_backend == "cli"


def test_agent_message_tokens_can_carry_usage():

    msg = AgentMessage(
        type="system",
        content="done",
        raw={
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_creation_input_tokens": 100,
                "cache_read_input_tokens": 400,
            }
        },
    )
    assert msg.raw["usage"]["input_tokens"] == 1000
    assert msg.raw["usage"]["output_tokens"] == 500
    assert msg.raw["usage"]["cache_creation_input_tokens"] == 100
    assert msg.raw["usage"]["cache_read_input_tokens"] == 400


def test_cli_backend_token_extraction_parse_result_event_extracts_tokens():

    backend = CLIBackend()

    # Simulate a result event with usage info
    event = {
        "type": "result",
        "subtype": "success",
        "usage": {
            "input_tokens": 1234,
            "output_tokens": 567,
        },
    }

    msgs = backend._parse_events(event)
    assert len(msgs) == 1
    assert msgs[0].raw.get("usage") == {"input_tokens": 1234, "output_tokens": 567}


def test_cli_backend_token_extraction_parse_result_event_without_usage():

    backend = CLIBackend()

    event = {
        "type": "result",
        "subtype": "success",
    }

    msgs = backend._parse_events(event)
    assert len(msgs) == 1
    # Should not error, usage may be absent
