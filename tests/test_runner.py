"""Tests for web/runner.py — Redis-based TaskRunner."""

import asyncio
import json
from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest

from web.agents.base import AgentMessage
from web.runner import TaskRunner, _persist_usage, _serialize_tool_event


async def _noop_stream(*args, **kwargs):
    return
    yield  # noqa: F841


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


def make_runner(mocker, fake_redis, max_concurrent=2):
    mock_backend = mocker.MagicMock()
    mock_backend.send_message = _noop_stream
    mock_backend.cancel = AsyncMock()
    mocker.patch("web.runner.get_agent", return_value=mock_backend)
    mocker.patch("web.runner.get_redis", return_value=fake_redis)
    mocker.patch("web.runner.config.MAX_CONCURRENT_AGENTS", max_concurrent)
    r = TaskRunner()
    return r


def make_event(type, content, raw=None):
    return AgentMessage(type=type, content=content, raw=raw or {})


@pytest.fixture
def runner(mocker, fake_redis):
    return make_runner(mocker, fake_redis)


def test_submit_pushes_to_redis(runner, fake_redis):
    async def _run():
        await runner.submit("c1", "hello", [])
        tasks = await fake_redis.lrange("autometa:tasks", 0, -1)
        assert len(tasks) == 1
        payload = json.loads(tasks[0])
        assert payload["conv_id"] == "c1"
        assert payload["prompt"] == "hello"

    asyncio.run(_run())


def test_cancel_publishes_and_updates_db(runner, mocker):
    mock_store = mocker.patch("web.runner.store")

    async def _run():
        await runner.cancel("c1")
        mock_store.update_conversation.assert_called_with("c1", needs_response=False)
        mock_store.add_message.assert_called_with("c1", "assistant", "*Interrompu.*")

    asyncio.run(_run())


def test_notify_publishes_update(runner, fake_redis):
    async def _run():
        pubsub = fake_redis.pubsub()
        await pubsub.subscribe("autometa:conv:c1")
        await pubsub.get_message()  # consume subscribe confirmation
        await runner.notify("c1")
        await asyncio.sleep(0.05)
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
        assert msg is not None and msg["data"] == "update"
        await pubsub.unsubscribe()

    asyncio.run(_run())


def test_notify_done_sets_key_and_publishes(runner, fake_redis):
    async def _run():
        await runner.notify_done("c1")
        assert await fake_redis.exists("autometa:done:c1")
        assert await runner.is_done("c1")

    asyncio.run(_run())


def test_is_done_false_for_unknown(runner):
    async def _run():
        assert not await runner.is_done("nonexistent")

    asyncio.run(_run())


def test_cleanup_removes_done_key(runner, fake_redis):
    async def _run():
        await runner.notify_done("c1")
        assert await runner.is_done("c1")
        await runner.cleanup("c1")
        assert not await runner.is_done("c1")

    asyncio.run(_run())


def test_subscribe_receives_messages(runner, fake_redis):
    async def _run():
        pubsub = await runner.subscribe("c1")
        await pubsub.get_message()  # consume subscribe confirmation
        await runner.notify("c1")
        await asyncio.sleep(0.05)
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
        assert msg is not None and msg["data"] == "update"
        await pubsub.unsubscribe()
        await pubsub.aclose()

    asyncio.run(_run())


def test_consumer_picks_task(mocker, fake_redis):
    runner = make_runner(mocker, fake_redis)
    mock_store = mocker.patch("web.runner.store")
    mock_conv = mocker.MagicMock()
    mock_conv.needs_response = True
    mock_store.get_conversation.return_value = mock_conv

    async def slow_stream(*a, **kw):
        await asyncio.sleep(10)
        yield

    runner.backend.send_message = slow_stream

    async def _run():
        await fake_redis.rpush(
            "autometa:tasks",
            json.dumps({
                "conv_id": "c1",
                "prompt": "hello",
                "history": [],
                "session_id": None,
                "user_email": None,
            }),
        )
        consumer = asyncio.create_task(runner._consumer_loop())
        await asyncio.sleep(0.5)
        assert "c1" in runner._running
        consumer.cancel()
        for t in runner._running.values():
            t.cancel()
        await asyncio.gather(consumer, *runner._running.values(), return_exceptions=True)

    asyncio.run(_run())


def test_consumer_skips_stale_task(mocker, fake_redis):
    runner = make_runner(mocker, fake_redis)
    mock_store = mocker.patch("web.runner.store")
    mock_conv = mocker.MagicMock()
    mock_conv.needs_response = False
    mock_store.get_conversation.return_value = mock_conv

    async def _run():
        await fake_redis.rpush(
            "autometa:tasks",
            json.dumps({
                "conv_id": "stale",
                "prompt": "old",
                "history": [],
                "session_id": None,
                "user_email": None,
            }),
        )
        consumer = asyncio.create_task(runner._consumer_loop())
        await asyncio.sleep(0.5)
        assert "stale" not in runner._running
        assert await fake_redis.llen("autometa:tasks") == 0
        consumer.cancel()
        await asyncio.gather(consumer, return_exceptions=True)

    asyncio.run(_run())


def test_run_agent_notifies_and_cleans_up(runner, mocker, fake_redis):
    mock_store = mocker.patch("web.runner.store")
    mock_msg = mocker.MagicMock()
    mock_msg.id = 42
    mock_store.add_message.return_value = mock_msg

    events = [make_event("assistant", "Hello")]

    async def mock_stream(*args, **kwargs):
        for e in events:
            yield e

    runner.backend.send_message = mock_stream

    async def _run():
        await runner._run_agent("c1", "prompt", [], None, None)
        mock_store.update_conversation.assert_called_with("c1", needs_response=False)
        assert await runner.is_done("c1")

    asyncio.run(_run())


def test_run_agent_clears_needs_response_on_error(runner, mocker, fake_redis):
    mock_store = mocker.patch("web.runner.store")

    async def mock_stream(*args, **kwargs):
        raise RuntimeError("boom")
        yield  # noqa: F841

    runner.backend.send_message = mock_stream

    async def _run():
        await runner._run_agent("c1", "prompt", [], None, None)
        mock_store.update_conversation.assert_called_with("c1", needs_response=False)
        assert await runner.is_done("c1")

    asyncio.run(_run())


def test_startup_clears_stuck_conversations(runner, mocker, fake_redis):
    mock_store = mocker.patch("web.runner.store")
    mock_store.get_running_conversation_ids.return_value = ["c1", "c2"]

    async def _run():
        await runner._recover_stuck(fake_redis)
        assert mock_store.add_message.call_count == 2

    asyncio.run(_run())


def test_serialize_tool_use_with_category(mocker):
    mocker.patch("web.runner.classify_tool", return_value="API: Matomo")
    event = make_event("tool_use", {"tool": "Bash", "input": {"command": "curl ..."}})
    result = json.loads(_serialize_tool_event(event, "c1", None))
    assert result["category"] == "API: Matomo"


def test_serialize_tool_result_with_api_calls(mocker):
    mocker.patch("web.runner.parse_api_signals", return_value=[{"source": "matomo"}])
    event = make_event("tool_result", {"output": "some output with signals"})
    result = json.loads(_serialize_tool_event(event, "c1", None))
    assert "api_calls" in result


def test_serialize_tool_result_without_api_calls(mocker):
    mocker.patch("web.runner.parse_api_signals", return_value=[])
    event = make_event("tool_result", "plain text output")
    assert _serialize_tool_event(event, "c1", None) == "plain text output"


def test_persist_usage(mocker):
    mock_store = mocker.patch("web.runner.store")
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    _persist_usage("c1", {"input_tokens": 100, "output_tokens": 50, "service_tier": "priority"})
    mock_store.accumulate_usage.assert_called_once_with(
        "c1",
        input_tokens=100,
        output_tokens=50,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        backend="cli",
        extra={"service_tier": "priority"},
    )


def test_persist_usage_no_extra(mocker):
    mock_store = mocker.patch("web.runner.store")
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    _persist_usage("c1", {"input_tokens": 10, "output_tokens": 5})
    call_kwargs = mock_store.accumulate_usage.call_args[1]
    assert call_kwargs["extra"] is None
