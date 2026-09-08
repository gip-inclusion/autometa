"""Un tour coupé par la limite d'usage est rejoué une fois sur le moteur de secours."""

import asyncio
import uuid

import fakeredis.aioredis
import pytest

from web import runner
from web.agents.base import AgentMessage
from web.runner import TaskRunner

RESET = "2026-09-08T20:00:00+00:00"


def _limit():
    # Why: _stream_turn vide event.raw après traitement — chaque test a besoin du sien.
    return AgentMessage(type="limit", content="limite", raw={"reset": RESET})


def _stream(*msgs):
    async def gen(**kwargs):
        for m in msgs:
            yield m

    return gen


def _backend(mocker, *events):
    b = mocker.MagicMock()
    b.send_message = _stream(*events)
    return b


def _recording_backend(mocker, sent):
    """Moteur qui répond « repris » et note dans `sent` les arguments qu'il a reçus."""
    b = mocker.MagicMock()

    def capture(**kwargs):
        sent.update(kwargs)
        return _stream(AgentMessage(type="assistant", content="repris"))()

    b.send_message = capture
    return b


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture(autouse=True)
def _isolate(mocker, fake_redis):
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    mocker.patch("web.runner.config.AGENT_FALLBACK_BACKEND", "cli-ollama")
    mocker.patch("web.runner.get_redis", return_value=fake_redis)
    mocker.patch("web.runner.session_sync")
    mocker.patch("web.runner._check_failure")
    mocker.patch("web.runner.history_for_turn", return_value=[])
    mocker.patch.object(runner.store, "update_conversation")
    mocker.patch.object(runner.store, "get_conversation", return_value=None)
    mocker.patch.object(runner.store, "add_message", return_value=mocker.Mock(id=1))
    mocker.patch.object(runner.store, "set_engine_state")
    mocker.patch.object(runner.store, "get_engine_state", return_value={"session_id": "s2", "seen_through": 3})


def test_limit_reroutes_once_to_the_fallback(mocker):
    marked = mocker.patch("web.runner.mark_backend_limited", new=mocker.AsyncMock())
    agents = mocker.patch(
        "web.runner.get_agent",
        side_effect=[
            _backend(mocker, _limit()),
            _backend(mocker, AgentMessage(type="assistant", content="repris")),
        ],
    )

    asyncio.run(TaskRunner()._run_agent("c1", "p", [], None, None, "s1", "cli"))

    marked.assert_awaited_once_with("cli", RESET)
    assert [c.args[0] for c in agents.call_args_list] == ["cli", "cli-ollama"]


def test_the_replay_resumes_the_fallback_session_and_its_catch_up(mocker):
    mocker.patch("web.runner.mark_backend_limited", new=mocker.AsyncMock())
    catchup = [{"role": "user", "content": "rattrapage"}]
    mocker.patch("web.runner.history_for_turn", return_value=catchup)
    sent = {}
    mocker.patch("web.runner.get_agent", side_effect=[_backend(mocker, _limit()), _recording_backend(mocker, sent)])

    asyncio.run(TaskRunner()._run_agent("c1", "p", [], None, None, "s1", "cli"))

    runner.history_for_turn.assert_called_once_with("c1", "s2", [], 3)
    runner.session_sync.download_session.assert_called_once_with("s2")
    assert sent["session_id"] == "s2"
    assert sent["history"] == catchup


def test_no_second_reroute_when_the_fallback_also_hits_a_limit(mocker):
    mocker.patch("web.runner.mark_backend_limited", new=mocker.AsyncMock())
    agents = mocker.patch("web.runner.get_agent", return_value=_backend(mocker, _limit()))

    asyncio.run(TaskRunner()._run_agent("c1", "p", [], None, None, "s2", "cli-ollama"))

    assert agents.call_count == 1


def test_no_reroute_without_a_fallback_configured(mocker):
    mocker.patch("web.runner.config.AGENT_FALLBACK_BACKEND", "")
    mocker.patch("web.runner.mark_backend_limited", new=mocker.AsyncMock())
    agents = mocker.patch("web.runner.get_agent", return_value=_backend(mocker, _limit()))

    asyncio.run(TaskRunner()._run_agent("c1", "p", [], None, None, "s1", "cli"))

    assert agents.call_count == 1


@pytest.mark.parametrize("fallback,session_id,backend", [("", "s1", "cli"), ("cli-ollama", "s2", "cli-ollama")])
def test_limit_message_is_written_when_no_reroute_happens(mocker, fallback, session_id, backend):
    mocker.patch("web.runner.config.AGENT_FALLBACK_BACKEND", fallback)
    mocker.patch("web.runner.get_agent", return_value=_backend(mocker, _limit()))

    asyncio.run(TaskRunner()._run_agent("c1", "p", [], None, None, session_id, backend))

    assert any(c.args[1] == "limit" for c in runner.store.add_message.call_args_list)


def test_no_limit_message_when_the_fallback_takes_over(mocker):
    mocker.patch("web.runner.mark_backend_limited", new=mocker.AsyncMock())
    mocker.patch(
        "web.runner.get_agent",
        side_effect=[_backend(mocker, _limit()), _backend(mocker, AgentMessage(type="assistant", content="repris"))],
    )

    asyncio.run(TaskRunner()._run_agent("c1", "p", [], None, None, "s1", "cli"))

    assert not any(c.args[1] == "limit" for c in runner.store.add_message.call_args_list)


def test_the_conversation_stays_open_until_the_fallback_answers(mocker):
    mocker.patch("web.runner.mark_backend_limited", new=mocker.AsyncMock())
    done = mocker.patch.object(TaskRunner, "notify_done", new=mocker.AsyncMock())
    observed = {}

    async def fallback_stream(**kwargs):
        observed["done"] = done.await_count
        observed["released"] = runner.store.update_conversation.call_count
        yield AgentMessage(type="assistant", content="repris")

    second = mocker.MagicMock()
    second.send_message = fallback_stream
    mocker.patch("web.runner.get_agent", side_effect=[_backend(mocker, _limit()), second])

    asyncio.run(TaskRunner()._run_agent("c1", "p", [], None, None, "s1", "cli"))

    assert observed == {"done": 0, "released": 0}
    done.assert_awaited_once_with("c1")
    runner.store.update_conversation.assert_called_once_with("c1", needs_response=False)


def test_a_successful_first_pass_still_advances_its_marker(mocker):
    mocker.patch("web.runner.get_agent", return_value=_backend(mocker, AgentMessage(type="assistant", content="ok")))

    asyncio.run(TaskRunner()._run_agent("c1", "p", [], None, None, "s1", "cli"))

    runner.store.set_engine_state.assert_called_once_with("c1", "cli", session_id="s1", seen_through=1)


def test_the_first_replay_mints_a_session_and_replays_the_whole_transcript(mocker):
    mocker.patch("web.runner.mark_backend_limited", new=mocker.AsyncMock())
    mocker.patch.object(runner.store, "get_engine_state", return_value={"session_id": None, "seen_through": None})
    transcript = [{"role": "user", "content": "tout"}]
    mocker.patch("web.runner.history_for_turn", return_value=transcript)
    sent = {}
    mocker.patch("web.runner.get_agent", side_effect=[_backend(mocker, _limit()), _recording_backend(mocker, sent)])

    asyncio.run(TaskRunner()._run_agent("c1", "p", [], None, None, "s1", "cli"))

    runner.session_sync.download_session.assert_not_called()
    assert uuid.UUID(sent["session_id"])
    runner.history_for_turn.assert_called_once_with("c1", sent["session_id"], [], None)
    assert sent["history"] == transcript


def test_a_failed_replay_setup_still_releases_the_conversation(mocker, fake_redis):
    mocker.patch("web.runner.mark_backend_limited", new=mocker.AsyncMock())
    done = mocker.patch.object(TaskRunner, "notify_done", new=mocker.AsyncMock())
    mocker.patch("web.runner.get_agent", return_value=_backend(mocker, _limit()))
    mocker.patch.object(runner.store, "get_engine_state", side_effect=RuntimeError("boum"))
    r = TaskRunner()

    async def _run():
        r._running["c1"] = asyncio.current_task()
        await fake_redis.set(f"{runner.PREFIX}:running:c1", "w1")
        await r._run_agent("c1", "p", [], None, None, "s1", "cli")
        return await fake_redis.exists(f"{runner.PREFIX}:running:c1")

    assert asyncio.run(_run()) == 0
    runner.store.update_conversation.assert_called_once_with("c1", needs_response=False)
    runner.store.add_message.assert_called_once_with("c1", "assistant", "limite")
    done.assert_awaited_once_with("c1")
    assert "c1" not in r._running


def test_a_failing_recovery_still_hands_the_conversation_back_to_the_sweep(mocker):
    mocker.patch("web.runner.mark_backend_limited", new=mocker.AsyncMock())
    mocker.patch("web.runner.get_agent", return_value=_backend(mocker, _limit()))
    mocker.patch.object(runner.store, "get_engine_state", side_effect=RuntimeError("postgres down"))
    mocker.patch.object(runner.store, "update_conversation", side_effect=RuntimeError("postgres down"))
    r = TaskRunner()

    async def _run():
        r._running["c1"] = asyncio.current_task()
        await r._run_agent("c1", "p", [], None, None, "s1", "cli")

    asyncio.run(_run())

    assert "c1" not in r._running


def test_the_replay_is_abandoned_when_a_newer_run_takes_over(mocker):
    mocker.patch("web.runner.mark_backend_limited", new=mocker.AsyncMock())
    agents = mocker.patch("web.runner.get_agent", return_value=_backend(mocker, _limit()))
    r = TaskRunner()

    def take_over(*args):
        r._running["c1"] = mocker.Mock()
        return {"session_id": "s2", "seen_through": 3}

    mocker.patch.object(runner.store, "get_engine_state", side_effect=take_over)

    asyncio.run(r._run_agent("c1", "p", [], None, None, "s1", "cli"))

    assert agents.call_count == 1
    runner.store.update_conversation.assert_not_called()


def test_a_successful_first_pass_still_releases_the_conversation(mocker):
    done = mocker.patch.object(TaskRunner, "notify_done", new=mocker.AsyncMock())
    mocker.patch("web.runner.get_agent", return_value=_backend(mocker, AgentMessage(type="assistant", content="ok")))

    asyncio.run(TaskRunner()._run_agent("c1", "p", [], None, None, "s1", "cli"))

    done.assert_awaited_once_with("c1")
    runner.store.update_conversation.assert_called_once_with("c1", needs_response=False)
