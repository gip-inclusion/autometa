"""Tests de web/runner.py prepare_turn — session native d'un moteur et rattrapage de ce qu'il a manqué."""

import uuid

import pytest

from web import catchup, runner
from web.agents.cli import CLIBackend
from web.database import Message


def _msg(msg_id, type_, content="x"):
    return Message(id=msg_id, conversation_id="c1", type=type_, content=content)


def _setup(mocker, transcript, *, session_id="sess-1", seen_through=None, resumable=True):
    """Transcript en base, état du moteur et présence de son fichier de session."""
    mocker.patch.object(
        runner.store, "get_engine_state", return_value={"session_id": session_id, "seen_through": seen_through}
    )
    mocker.patch.object(
        runner.store, "get_messages_since", side_effect=lambda conv_id, after: [m for m in transcript if m.id > after]
    )
    mocker.patch.object(runner.session_sync, "download_session")
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: resumable))


def _contents(turn):
    return [e["content"] for e in turn.history]


def test_an_engine_without_state_gets_its_own_session_not_the_primary_one(mocker):
    """B1 : le secours qui prend la main pour la première fois ne reprend jamais la session Claude —
    il en ouvre une neuve, amorcée par le rattrapage borné."""
    _setup(
        mocker,
        [_msg(1, "user", "Q1"), _msg(2, "assistant", "R1"), _msg(3, "user", "Q2")],
        session_id=None,
        resumable=False,
    )

    turn = runner.prepare_turn("c1", "cli-ollama")

    assert uuid.UUID(turn.session_id)
    runner.session_sync.download_session.assert_not_called()
    assert _contents(turn) == ["Q1", "R1"]
    assert turn.question_id == 3


def test_an_engine_with_state_resumes_its_own_session(mocker):
    _setup(mocker, [_msg(1, "user", "Q1"), _msg(2, "assistant", "R1"), _msg(3, "user", "Q2")], seen_through=1)

    turn = runner.prepare_turn("c1", "cli")

    runner.session_sync.download_session.assert_called_once_with("sess-1")
    assert (turn.session_id, turn.history, turn.question_id) == ("sess-1", [], 3)


def test_only_messages_after_the_marker_are_loaded(mocker):
    """B8 : le transcript entier n'est pas relu à chaque tour."""
    _setup(mocker, [_msg(1, "user"), _msg(2, "assistant"), _msg(3, "user")], seen_through=1)

    runner.prepare_turn("c1", "cli")

    runner.store.get_messages_since.assert_called_once_with("c1", 1)


@pytest.mark.parametrize(
    "noise",
    [
        _msg(3, "assistant", "*Interrompu.*"),
        _msg(3, "assistant", "*Budget de 50 appels d'outils dépassé*"),
        _msg(3, "assistant", "Cette conversation devient complexe"),
    ],
)
def test_what_follows_the_engines_own_turn_is_not_replayed(mocker, noise):
    """B2 : un tour annulé ou suivi d'une alerte laisse des messages que la session a déjà, ou qui ne
    sont que du bruit — le prochain tour n'en reçoit rien, avec ou sans secours."""
    _setup(
        mocker, [_msg(1, "user", "Q1"), _msg(2, "assistant", "partiel"), noise, _msg(4, "user", "Q2")], seen_through=1
    )

    turn = runner.prepare_turn("c1", "cli")

    assert turn.history == []
    assert CLIBackend()._build_prompt("Q2", turn.history) == "Q2"


def test_the_catch_up_holds_the_other_engines_turns_up_to_the_question(mocker):
    _setup(
        mocker,
        [
            _msg(1, "user", "Q1"),
            _msg(2, "assistant", "R1 à moi"),
            _msg(3, "user", "Q2"),
            _msg(4, "tool_use", '{"tool": "Read", "input": {"file_path": "/a"}}'),
            _msg(5, "assistant", "R2 du secours"),
            _msg(6, "user", "Q3"),
        ],
        seen_through=1,
    )

    turn = runner.prepare_turn("c1", "cli")

    assert _contents(turn) == ["Q2", '[appel Read] {"file_path": "/a"}', "R2 du secours"]
    assert turn.question_id == 6


def test_the_question_is_cut_by_id_even_when_output_follows_it(mocker):
    """B5 : le primaire a émis du texte avant la limite — la question n'est plus en dernière position,
    mais elle n'entre toujours pas dans le rattrapage du secours."""
    _setup(
        mocker,
        [_msg(1, "user", "Q1"), _msg(2, "assistant", "R1"), _msg(3, "user", "Q2"), _msg(4, "assistant", "début")],
        seen_through=0,
    )

    turn = runner.prepare_turn("c1", "cli-ollama")

    assert _contents(turn) == ["Q1", "R1"]
    assert turn.question_id == 3


def test_a_session_from_before_multi_engine_is_resumed_without_catch_up(mocker):
    _setup(mocker, [_msg(1, "user"), _msg(2, "assistant"), _msg(3, "user")], seen_through=None)

    turn = runner.prepare_turn("c1", "cli")

    assert (turn.history, turn.question_id) == ([], 3)


@pytest.mark.parametrize("had_session, alerted", [(False, False), (True, True)])
def test_a_missing_session_alerts_only_when_the_engine_had_one(mocker, had_session, alerted):
    """Première main d'un moteur : pas de fichier, rien d'anormal. Un fichier perdu, en revanche, se signale."""
    _setup(
        mocker, [_msg(1, "user", "Q1"), _msg(2, "user", "Q2")], session_id="s" if had_session else None, resumable=False
    )
    capture = mocker.patch.object(runner.sentry_sdk, "capture_message")

    turn = runner.prepare_turn("c1", "cli")

    assert _contents(turn) == ["Q1"]
    assert capture.called is alerted


def test_every_bootstrap_is_journalised_with_its_size(mocker):
    """L'amorçage envoie le transcript au moteur, donc à un tiers quand c'est le secours : il se trace."""
    _setup(mocker, [_msg(1, "user", "bonjour"), _msg(2, "user", "Q2")], session_id=None, resumable=False)
    warn = mocker.patch.object(runner.logger, "warning")

    runner.prepare_turn("c1", "cli-ollama")

    logged = [c for c in warn.call_args_list if c.args[0] == "agent.session.bootstrap"]
    assert len(logged) == 1
    assert logged[0].kwargs["extra"]["agent.bootstrap_chars"] == len("bonjour")


def test_bootstrapping_a_session_is_capped_like_a_catch_up(mocker):
    transcript = [_msg(1, "user"), *[_msg(i, "assistant", "x" * 5000) for i in range(2, 22)], _msg(22, "user")]
    _setup(mocker, transcript, session_id=None, resumable=False)

    turn = runner.prepare_turn("c1", "cli-ollama")

    assert sum(len(e["content"]) for e in turn.history) <= catchup.TOTAL_CAP
