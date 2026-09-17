"""Tests for web/runner.py history_for_turn — resume vs full-history fallback."""

import pytest

from web import catchup, runner
from web.agents.cli import CLIBackend
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


def test_the_message_being_submitted_is_not_replayed_in_the_catchup(mocker):
    """La route stocke le message utilisateur avant de soumettre le tour : sans ce retrait il serait
    rendu dans le rattrapage *et* ajouté comme prompt, donc posé deux fois au moteur."""
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: True))
    msgs = [_msg(1, "user", "Q1"), _msg(2, "assistant", "R1"), _msg(3, "user", "Q2")]
    mocker.patch.object(runner.store, "get_conversation", return_value=_conv(msgs))

    assert runner.history_for_turn("c1", "sess-1", [], seen_through=2) == []


def test_the_degenerate_turn_sends_the_bare_message_to_the_cli(mocker):
    """Non-régression : moteur unique, tour n>1 — le prompt reste le message seul, sans préfixe."""
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: True))
    msgs = [_msg(1, "user", "Q1"), _msg(2, "assistant", "R1"), _msg(3, "user", "Q2")]
    mocker.patch.object(runner.store, "get_conversation", return_value=_conv(msgs))

    history = runner.history_for_turn("c1", "sess-1", [], seen_through=2)

    assert CLIBackend()._build_prompt("Q2", history) == "Q2"


def test_a_catchup_keeps_everything_but_the_message_being_submitted(mocker):
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: True))
    msgs = [_msg(1, "assistant", "vu"), _msg(2, "user", "Q1"), _msg(3, "assistant", "R1"), _msg(4, "user", "Q2")]
    mocker.patch.object(runner.store, "get_conversation", return_value=_conv(msgs))

    result = runner.history_for_turn("c1", "sess-1", [], seen_through=1)

    assert result == [{"role": "user", "content": "Q1"}, {"role": "assistant", "content": "R1"}]


@pytest.mark.parametrize("session_is_new, alerted", [(True, False), (False, True)])
def test_a_missing_session_alerts_only_when_the_engine_had_one(mocker, session_is_new, alerted):
    """Première main du moteur de secours : pas de fichier de session, donc rien d'anormal à signaler
    — sinon chaque conversation active crie « resume cassé » au pire moment."""
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: False))
    mocker.patch.object(runner.store, "get_conversation", return_value=_conv([_msg(1, "assistant", "b")]))
    capture = mocker.patch.object(runner.sentry_sdk, "capture_message")
    warn = mocker.patch.object(runner.logger, "warning")

    result = runner.history_for_turn("c1", "sess-1", [], session_is_new=session_is_new)

    assert result == [{"role": "assistant", "content": "b"}]
    assert capture.called is alerted
    assert any("Session file" in str(c.args[0]) for c in warn.call_args_list) is alerted


def test_every_bootstrap_is_journalised_with_its_size(mocker):
    """L'amorçage est le seul endroit où une conversation entière quitte le service : il se trace
    même quand il est normal (première main d'un moteur), sinon l'égress est invisible."""
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: False))
    mocker.patch.object(runner.store, "get_conversation", return_value=_conv([_msg(1, "assistant", "bonjour")]))
    warn = mocker.patch.object(runner.logger, "warning")

    runner.history_for_turn("c1", "sess-1", [], session_is_new=True)

    logged = [c for c in warn.call_args_list if c.args[0] == "agent.session.bootstrap"]
    assert len(logged) == 1
    assert logged[0].kwargs["extra"]["agent.bootstrap_chars"] == len("bonjour")


def test_bootstrapping_a_session_is_capped_like_a_catchup(mocker):
    """Au premier basculement le moteur de secours n'a pas de session : sans plafond, tout le
    transcript — donc des analyses sur des candidats — partirait chez un tiers d'un seul bloc."""
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: False))
    msgs = [_msg(i, "assistant", "x" * 5000) for i in range(1, 21)]
    mocker.patch.object(runner.store, "get_conversation", return_value=_conv(msgs))

    result = runner.history_for_turn("c1", "sess-1", [], session_is_new=True)

    assert sum(len(e["content"]) for e in result) <= catchup.TOTAL_CAP
    assert len(result) < len(msgs)


def test_session_missing_still_wins_over_catchup(mocker):
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: False))
    msgs = [_msg(1, "user", "a"), _msg(2, "assistant", "b"), _msg(3, "user", "c")]
    mocker.patch.object(runner.store, "get_conversation", return_value=_conv(msgs))

    result = runner.history_for_turn("c1", "sess-1", [], seen_through=2)

    assert result == [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
