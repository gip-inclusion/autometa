"""Le repère par moteur n'avance que sur un tour complet."""

import asyncio
import itertools

import fakeredis.aioredis
import pytest

from web import runner
from web.agents.base import AgentMessage
from web.runner import TaskRunner


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
    mocker.patch.object(runner.store, "update_conversation")
    mocker.patch.object(runner.store, "get_conversation", return_value=None)
    # Why: des ids croissants distinguent le message qui alimente le repère de tous les autres —
    # un id figé laisserait passer un repère nourri par la branche `system` ou `limit`.
    mocker.patch.object(runner.store, "add_message", side_effect=(mocker.Mock(id=i) for i in itertools.count(10)))
    backend = mocker.MagicMock()
    backend.send_message = _stream(*events)
    mocker.patch("web.runner.get_agent", return_value=backend)
    return TaskRunner()


def test_marker_advances_to_the_last_message_of_the_turn(mocker, fake_redis):
    """Le repère suit le dernier message du transcript — pas le dernier `add_message` : un
    événement `system` est stocké mais ne fait pas partie de ce que le moteur a vu."""
    set_state = mocker.patch.object(runner.store, "set_engine_state")
    r = _make(
        mocker,
        fake_redis,
        AgentMessage(type="assistant", content="un"),
        AgentMessage(type="tool_use", content={"tool": "Read", "input": {}}),
        AgentMessage(type="tool_result", content={"output": "ok"}),
        AgentMessage(type="assistant", content="deux"),
        AgentMessage(type="system", content="retry", raw={"subtype": "api_retry"}),
    )

    asyncio.run(r._run_agent("c1", "p", [], None, None, "sess-1", "cli"))

    set_state.assert_called_once_with("c1", "cli", session_id="sess-1", seen_through=13)


def test_marker_does_not_advance_when_the_turn_hits_a_limit(mocker, fake_redis):
    set_state = mocker.patch.object(runner.store, "set_engine_state")
    progress = AgentMessage(type="assistant", content="en cours")
    limit = AgentMessage(type="limit", content="limite", raw={"reset": None})
    r = _make(mocker, fake_redis, progress, limit)

    asyncio.run(r._run_agent("c1", "p", [], None, None, "sess-1", "cli"))

    set_state.assert_not_called()
