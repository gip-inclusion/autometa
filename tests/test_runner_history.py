"""Tests for web/runner.py history_for_turn — resume vs full-history fallback."""

from web import runner
from web.database import Message


def _conv(messages):
    class Conv:
        def __init__(self, msgs):
            self.messages = msgs

    return Conv(messages)


def test_returns_default_when_session_id_missing(mocker):
    spy = mocker.patch.object(runner.store, "get_conversation")
    assert runner.history_for_turn("c1", None, []) == []
    spy.assert_not_called()


def test_returns_default_when_session_file_exists(mocker):
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: True))
    spy = mocker.patch.object(runner.store, "get_conversation")
    assert runner.history_for_turn("c1", "sess-1", []) == []
    spy.assert_not_called()


def test_rebuilds_full_history_when_session_file_missing(mocker):
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: False))
    msgs = [
        Message(type="user", content="set secret X"),
        Message(type="assistant", content="noted"),
        Message(type="tool_use", content="{}"),
        Message(type="user", content="what is the secret?"),
    ]
    mocker.patch.object(runner.store, "get_conversation", return_value=_conv(msgs))

    result = runner.history_for_turn("c1", "sess-1", [])

    assert result == [
        {"role": "user", "content": "set secret X"},
        {"role": "assistant", "content": "noted"},
    ]
    runner.store.get_conversation.assert_called_once_with("c1", include_messages=True)


def test_returns_empty_when_no_user_or_assistant_messages(mocker):
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: False))
    msgs = [Message(type="tool_use", content="{}"), Message(type="tool_result", content="{}")]
    mocker.patch.object(runner.store, "get_conversation", return_value=_conv(msgs))
    assert runner.history_for_turn("c1", "sess-1", []) == []


def test_rebuild_returns_default_when_conversation_gone(mocker):
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: False))
    mocker.patch.object(runner.store, "get_conversation", return_value=None)
    assert runner.history_for_turn("c1", "sess-1", []) == []
