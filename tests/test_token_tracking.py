"""Tests for usage tracking across backends."""

import pytest
import tempfile
import os
from pathlib import Path


class TestConversationUsageFields:
    """Tests for usage fields on Conversation dataclass."""

    def test_conversation_has_usage_input_tokens_field(self):
        """Conversation dataclass has usage_input_tokens field defaulting to 0."""
        from web.database import Conversation

        conv = Conversation()
        assert hasattr(conv, 'usage_input_tokens')
        assert conv.usage_input_tokens == 0

    def test_conversation_has_usage_output_tokens_field(self):
        """Conversation dataclass has usage_output_tokens field defaulting to 0."""
        from web.database import Conversation

        conv = Conversation()
        assert hasattr(conv, 'usage_output_tokens')
        assert conv.usage_output_tokens == 0

    def test_conversation_has_usage_cache_creation_tokens_field(self):
        """Conversation dataclass has usage_cache_creation_tokens field defaulting to 0."""
        from web.database import Conversation

        conv = Conversation()
        assert hasattr(conv, 'usage_cache_creation_tokens')
        assert conv.usage_cache_creation_tokens == 0

    def test_conversation_has_usage_cache_read_tokens_field(self):
        """Conversation dataclass has usage_cache_read_tokens field defaulting to 0."""
        from web.database import Conversation

        conv = Conversation()
        assert hasattr(conv, 'usage_cache_read_tokens')
        assert conv.usage_cache_read_tokens == 0

    def test_conversation_has_usage_backend_field(self):
        """Conversation dataclass has usage_backend field defaulting to None."""
        from web.database import Conversation

        conv = Conversation()
        assert hasattr(conv, 'usage_backend')
        assert conv.usage_backend is None

    def test_conversation_has_usage_extra_field(self):
        """Conversation dataclass has usage_extra field defaulting to None."""
        from web.database import Conversation

        conv = Conversation()
        assert hasattr(conv, 'usage_extra')
        assert conv.usage_extra is None

    def test_conversation_to_dict_includes_usage_fields(self):
        """Conversation.to_dict() includes all usage fields."""
        from web.database import Conversation

        conv = Conversation(
            usage_input_tokens=100,
            usage_output_tokens=50,
            usage_cache_creation_tokens=20,
            usage_cache_read_tokens=80,
            usage_backend='cli',
            usage_extra={'service_tier': 'standard'},
        )
        data = conv.to_dict()
        assert data['usage_input_tokens'] == 100
        assert data['usage_output_tokens'] == 50
        assert data['usage_cache_creation_tokens'] == 20
        assert data['usage_cache_read_tokens'] == 80
        assert data['usage_backend'] == 'cli'
        assert data['usage_extra'] == {'service_tier': 'standard'}


class TestDatabaseUsageColumns:
    """Tests for usage columns in database schema."""

    @pytest.fixture
    def temp_db(self, tmp_path, monkeypatch):
        """Create a temporary database for testing."""
        db_path = tmp_path / "test.db"
        monkeypatch.setattr('web.config.SQLITE_PATH', db_path)
        # Re-import to use patched path
        import importlib
        import web.database
        importlib.reload(web.database)
        return db_path

    def test_conversations_table_has_usage_columns(self, temp_db):
        """Conversations table has all usage columns."""
        from web.database import init_db, get_db

        init_db()

        with get_db() as conn:
            cursor = conn.execute("PRAGMA table_info(conversations)")
            columns = {row['name'] for row in cursor.fetchall()}
            assert 'usage_input_tokens' in columns
            assert 'usage_output_tokens' in columns
            assert 'usage_cache_creation_tokens' in columns
            assert 'usage_cache_read_tokens' in columns
            assert 'usage_backend' in columns
            assert 'usage_extra' in columns

    def test_create_conversation_stores_zero_usage(self, temp_db):
        """New conversations start with zero usage."""
        from web.database import ConversationStore

        store = ConversationStore()
        conv = store.create_conversation(user_id="test")

        loaded = store.get_conversation(conv.id)
        assert loaded.usage_input_tokens == 0
        assert loaded.usage_output_tokens == 0
        assert loaded.usage_cache_creation_tokens == 0
        assert loaded.usage_cache_read_tokens == 0
        assert loaded.usage_backend is None
        assert loaded.usage_extra is None

    def test_update_conversation_usage(self, temp_db):
        """Can update usage on a conversation."""
        from web.database import ConversationStore

        store = ConversationStore()
        conv = store.create_conversation(user_id="test")

        # Update usage
        store.update_conversation_usage(
            conv.id,
            input_tokens=1500,
            output_tokens=800,
            cache_creation_tokens=100,
            cache_read_tokens=500,
            backend='sdk',
            extra={'service_tier': 'priority', 'web_search_requests': 2},
        )

        loaded = store.get_conversation(conv.id)
        assert loaded.usage_input_tokens == 1500
        assert loaded.usage_output_tokens == 800
        assert loaded.usage_cache_creation_tokens == 100
        assert loaded.usage_cache_read_tokens == 500
        assert loaded.usage_backend == 'sdk'
        assert loaded.usage_extra == {'service_tier': 'priority', 'web_search_requests': 2}

    def test_accumulate_usage(self, temp_db):
        """Can accumulate usage incrementally."""
        from web.database import ConversationStore

        store = ConversationStore()
        conv = store.create_conversation(user_id="test")

        # First exchange
        store.accumulate_usage(
            conv.id,
            input_tokens=100,
            output_tokens=50,
            cache_creation_tokens=10,
            cache_read_tokens=0,
            backend='cli',
        )
        loaded = store.get_conversation(conv.id)
        assert loaded.usage_input_tokens == 100
        assert loaded.usage_output_tokens == 50
        assert loaded.usage_cache_creation_tokens == 10
        assert loaded.usage_cache_read_tokens == 0
        assert loaded.usage_backend == 'cli'

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
        assert loaded.usage_backend == 'cli'


class TestAgentMessageTokens:
    """Tests for token information in AgentMessage."""

    def test_agent_message_can_carry_usage(self):
        """AgentMessage can carry token usage in raw dict."""
        from web.agents.base import AgentMessage

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
            }
        )
        assert msg.raw['usage']['input_tokens'] == 1000
        assert msg.raw['usage']['output_tokens'] == 500
        assert msg.raw['usage']['cache_creation_input_tokens'] == 100
        assert msg.raw['usage']['cache_read_input_tokens'] == 400


class TestCLIBackendTokenExtraction:
    """Tests for token extraction from CLI backend."""

    def test_parse_result_event_extracts_tokens(self):
        """CLI backend extracts tokens from result event."""
        from web.agents.cli import CLIBackend

        backend = CLIBackend()

        # Simulate a result event with usage info
        event = {
            "type": "result",
            "subtype": "success",
            "usage": {
                "input_tokens": 1234,
                "output_tokens": 567,
            }
        }

        msg = backend._parse_event(event)
        assert msg is not None
        assert msg.raw.get('usage') == {"input_tokens": 1234, "output_tokens": 567}

    def test_parse_result_event_without_usage(self):
        """CLI backend handles result event without usage gracefully."""
        from web.agents.cli import CLIBackend

        backend = CLIBackend()

        event = {
            "type": "result",
            "subtype": "success",
        }

        msg = backend._parse_event(event)
        assert msg is not None
        # Should not error, usage may be absent


class TestSDKBackendTokenExtraction:
    """Tests for token extraction from SDK backend."""

    def test_normalize_result_message_extracts_tokens(self):
        """SDK backend extracts tokens from ResultMessage."""
        from unittest.mock import MagicMock

        # Import SDK backend - it will use the classes from claude_agent_sdk
        from web.agents.sdk import SDKBackend, ResultMessage

        backend = SDKBackend()

        # Create a subclass that isinstance will recognize
        class MockResultMessage(ResultMessage):
            def __init__(self):
                # Don't call super().__init__() - just set attributes
                self.subtype = 'success'
                self.usage = MagicMock()
                self.usage.input_tokens = 2000
                self.usage.output_tokens = 1000
                self.usage.cache_creation_input_tokens = 100
                self.usage.cache_read_input_tokens = 500
                self.usage.service_tier = None
                self.usage.server_tool_use = None

        mock_result = MockResultMessage()

        messages = backend._normalize_message(mock_result)
        assert len(messages) >= 1

        # Find the system message
        system_msg = next((m for m in messages if m.type == "system"), None)
        assert system_msg is not None
        usage = system_msg.raw.get('usage')
        assert usage['input_tokens'] == 2000
        assert usage['output_tokens'] == 1000
        assert usage['cache_creation_input_tokens'] == 100
        assert usage['cache_read_input_tokens'] == 500
