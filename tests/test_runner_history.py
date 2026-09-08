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


def test_discards_default_history_when_session_present_and_nothing_new(mocker):
    """/relaunch submits the full transcript as default_history alongside session_id — it must be
    discarded, not replayed on top of the resumed session (which already has it)."""
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: True))
    spy = mocker.patch.object(runner.store, "get_conversation")

    result = runner.history_for_turn("c1", "sess-1", [{"role": "user", "content": "full transcript"}])

    assert result == []
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


def _msg(msg_id, type_, content):
    return Message(id=msg_id, conversation_id="c1", type=type_, content=content)


def test_returns_catchup_when_session_exists_and_something_happened(mocker):
    """Ids out of storage order (a same-timestamp tie) must still render oldest-first — pins the
    explicit sort by id before build_catchup, not just get_conversation's own timestamp order."""
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: True))
    msgs = [
        _msg(1, "user", "vu"),
        _msg(2, "assistant", "déjà vu"),
        _msg(4, "tool_use", '{"tool": "Read", "input": {"file_path": "/a"}}'),
        _msg(3, "assistant", "nouveau"),
    ]
    mocker.patch.object(runner.store, "get_conversation", return_value=_conv(msgs))

    result = runner.history_for_turn("c1", "sess-1", [], seen_through=2)

    assert [e["content"] for e in result] == ["nouveau", '[appel Read] {"file_path": "/a"}']


def test_returns_empty_catchup_when_nothing_happened_since(mocker):
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: True))
    msgs = [_msg(1, "user", "vu"), _msg(2, "assistant", "déjà vu")]
    mocker.patch.object(runner.store, "get_conversation", return_value=_conv(msgs))

    assert runner.history_for_turn("c1", "sess-1", [], seen_through=2) == []


def test_session_missing_still_wins_over_catchup(mocker):
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: False))
    msgs = [_msg(1, "user", "a"), _msg(2, "assistant", "b"), _msg(3, "user", "c")]
    mocker.patch.object(runner.store, "get_conversation", return_value=_conv(msgs))

    result = runner.history_for_turn("c1", "sess-1", [], seen_through=2)

    assert result == [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
