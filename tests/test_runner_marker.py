"""Le repère par moteur : la question du tour, ou juste avant elle quand la limite a coupé le tour."""

import asyncio

import fakeredis.aioredis
import pytest

from web import runner
from web.agents.base import AgentMessage
from web.runner import EngineTurn, TaskRunner


def _stream(*msgs):
    async def gen(**kwargs):
        for m in msgs:
            yield m

    return gen


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


def _make(mocker, fake_redis, *events):
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    mocker.patch("web.runner.config.AGENT_FALLBACK_BACKEND", "")
    mocker.patch("web.runner.get_redis", return_value=fake_redis)
    mocker.patch("web.runner.session_sync")
    mocker.patch("web.runner._check_failure")
    mocker.patch.object(TaskRunner, "_alert_usage_limit_once", new=mocker.AsyncMock())
    mocker.patch.object(runner.store, "update_conversation")
    mocker.patch.object(runner.store, "get_conversation", return_value=None)
    mocker.patch.object(runner.store, "add_message", return_value=mocker.Mock(id=99))
    backend = mocker.MagicMock()
    backend.send_message = _stream(*events)
    mocker.patch("web.runner.get_agent", return_value=backend)
    return TaskRunner()


@pytest.mark.parametrize(
    "event",
    [
        AgentMessage(type="assistant", content="réponse"),
        AgentMessage(type="error", content="boum"),
        AgentMessage(type="system", content="retry", raw={"subtype": "api_retry"}),
    ],
)
def test_the_marker_moves_to_the_question_whatever_the_outcome(mocker, fake_redis, event):
    """B2 : la session du moteur contient la question dès qu'il l'a reçue — réussite, erreur ou
    annulation, le prochain rattrapage ne doit pas la lui renvoyer."""
    set_state = mocker.patch.object(runner.store, "set_engine_state")
    r = _make(mocker, fake_redis, event)

    asyncio.run(r._run_agent("c1", "p", None, None, EngineTurn("cli", "sess-1", [], 7)))

    set_state.assert_called_once_with("c1", "cli", session_id="sess-1", seen_through=7)


def test_a_limited_turn_stops_the_marker_just_before_its_question(mocker, fake_redis):
    """B4 : même au tout premier tour, le primaire coupé par la limite garde un repère — à son retour
    il rattrape la question et tout ce que le secours a répondu depuis."""
    set_state = mocker.patch.object(runner.store, "set_engine_state")
    mocker.patch("web.runner.mark_backend_limited", new=mocker.AsyncMock())
    limit = AgentMessage(type="limit", content="limite", raw={"reset": "2026-09-08T20:00:00+00:00"})
    r = _make(mocker, fake_redis, AgentMessage(type="assistant", content="en cours"), limit)

    asyncio.run(r._run_agent("c1", "p", None, None, EngineTurn("cli", "sess-1", [], 7)))

    set_state.assert_called_once_with("c1", "cli", session_id="sess-1", seen_through=6)


def test_a_primary_back_from_its_limit_catches_up_on_the_fallback_turns(mocker):
    """B4 de bout en bout : repère posé par la limite, puis rattrapage calculé à partir de lui."""
    messages = [
        mocker.Mock(id=7, type="user", content="Q1"),
        mocker.Mock(id=8, type="assistant", content="R1 du secours"),
        mocker.Mock(id=9, type="user", content="Q2"),
    ]
    mocker.patch.object(runner.store, "get_engine_state", return_value={"session_id": "sess-1", "seen_through": 6})
    mocker.patch.object(
        runner.store, "get_messages_since", side_effect=lambda c, after: [m for m in messages if m.id > after]
    )
    mocker.patch.object(runner.session_sync, "download_session")
    mocker.patch.object(runner.session_sync, "get_session_path", return_value=mocker.Mock(exists=lambda: True))

    turn = runner.prepare_turn("c1", "cli")

    assert [e["content"] for e in turn.history] == ["Q1", "R1 du secours"]
