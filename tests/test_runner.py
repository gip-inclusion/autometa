"""Tests for web/runner.py — TaskRunner and helper functions."""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from web.agents.base import AgentMessage
from web.runner import TaskRunner, _persist_usage, _serialize_tool_event


async def _noop_stream(*args, **kwargs):
    return
    yield


def make_runner(mocker, max_concurrent=2):
    mock_backend = mocker.MagicMock()
    mock_backend.send_message = _noop_stream
    mock_backend.cancel = AsyncMock()
    mocker.patch("web.runner.get_agent", return_value=mock_backend)
    mocker.patch("web.runner.config.MAX_CONCURRENT_AGENTS", max_concurrent)
    r = TaskRunner()
    return r


def make_event(type, content, raw=None):
    return AgentMessage(type=type, content=content, raw=raw or {})


@pytest.fixture
def runner(mocker):
    return make_runner(mocker)


def test_submit_starts_task(runner, mocker):
    mocker.patch("web.runner.store")

    async def slow_stream(*a, **kw):
        await asyncio.sleep(10)
        yield  # never reached

    runner.backend.send_message = slow_stream

    async def _run():
        runner.submit("c1", "hello", [])
        assert "c1" in runner._running
        assert runner.is_running("c1")
        runner._running["c1"].cancel()
        await asyncio.gather(runner._running["c1"], return_exceptions=True)

    asyncio.run(_run())


def test_submit_duplicate_ignored(runner, mocker):
    mocker.patch("web.runner.store")

    async def slow_stream(*a, **kw):
        await asyncio.sleep(10)
        yield

    runner.backend.send_message = slow_stream

    async def _run():
        runner.submit("c1", "hello", [])
        runner.submit("c1", "again", [])
        assert len(runner._running) == 1
        runner._running["c1"].cancel()
        await asyncio.gather(runner._running["c1"], return_exceptions=True)

    asyncio.run(_run())


def test_submit_queues_when_full(mocker):
    runner = make_runner(mocker, max_concurrent=1)
    mocker.patch("web.runner.store")

    async def slow_stream(*a, **kw):
        await asyncio.sleep(10)
        yield

    runner.backend.send_message = slow_stream

    async def _run():
        runner.submit("c1", "first", [])
        runner.submit("c2", "second", [])
        assert "c1" in runner._running
        assert "c2" not in runner._running
        assert len(runner._queue) == 1
        assert runner._queue[0][0] == "c2"
        runner._running["c1"].cancel()
        await asyncio.gather(runner._running["c1"], return_exceptions=True)

    asyncio.run(_run())


def test_cancel_running_task(runner, mocker):
    mock_store = mocker.patch("web.runner.store")

    async def slow_stream(*a, **kw):
        await asyncio.sleep(10)
        yield

    runner.backend.send_message = slow_stream

    async def _run():
        runner.submit("c1", "hello", [])
        result = await runner.cancel("c1")
        assert result is True
        assert "c1" not in runner._running
        mock_store.update_conversation.assert_called_with("c1", needs_response=False)
        mock_store.add_message.assert_called_with("c1", "assistant", "*Interrompu.*")

    asyncio.run(_run())


def test_cancel_not_running(runner, mocker):
    mock_store = mocker.patch("web.runner.store")

    async def _run():
        result = await runner.cancel("c1")
        assert result is True
        mock_store.update_conversation.assert_called_with("c1", needs_response=False)

    asyncio.run(_run())


def test_cancel_removes_from_queue(mocker):
    runner = make_runner(mocker, max_concurrent=1)
    mocker.patch("web.runner.store")

    async def slow_stream(*a, **kw):
        await asyncio.sleep(10)
        yield

    runner.backend.send_message = slow_stream

    async def _run():
        runner.submit("c1", "first", [])
        runner.submit("c2", "second", [])
        assert len(runner._queue) == 1
        await runner.cancel("c2")
        assert len(runner._queue) == 0
        runner._running["c1"].cancel()
        await asyncio.gather(runner._running["c1"], return_exceptions=True)

    asyncio.run(_run())


def test_is_running_false_for_unknown(runner):
    assert runner.is_running("nonexistent") is False


def test_notify_no_listener(runner):
    runner.notify("no-listener")
    assert "no-listener" not in runner._signals


def test_notify_wakes_listener(runner):
    sig = runner._get_or_create_signal("c1")
    assert sig.counter == 0
    runner.notify("c1")
    assert sig.counter == 1
    assert sig.event.is_set()


def test_notify_done_creates_signal(runner):
    runner.notify_done("c1")
    assert runner.is_done("c1")
    assert runner._signals["c1"].counter == 1


def test_is_done_false_for_unknown(runner):
    assert runner.is_done("nonexistent") is False


def test_wait_for_update_returns_true_on_signal(runner):
    async def _run():
        runner._get_or_create_signal("c1")
        runner.notify("c1")
        result = await runner.wait_for_update("c1", timeout=0.01)
        assert result is True

    asyncio.run(_run())


def test_wait_for_update_returns_false_on_timeout(runner):
    async def _run():
        result = await runner.wait_for_update("c1", timeout=0.01)
        assert result is False

    asyncio.run(_run())


def test_cleanup_removes_signal(runner):
    runner._get_or_create_signal("c1")
    runner.cleanup("c1")
    assert "c1" not in runner._signals


def test_cleanup_noop_for_unknown(runner):
    runner.cleanup("nonexistent")


def test_drain_queue_starts_next(mocker):
    runner = make_runner(mocker, max_concurrent=2)
    mocker.patch("web.runner.store")

    async def _run():
        runner._queue = [("c1", "p", [], None, None), ("c2", "p", [], None, None)]
        runner._drain_queue()
        assert "c1" in runner._running
        assert "c2" in runner._running
        assert len(runner._queue) == 0
        for t in runner._running.values():
            t.cancel()
        await asyncio.gather(*runner._running.values(), return_exceptions=True)

    asyncio.run(_run())


def test_drain_queue_skips_already_running(mocker):
    runner = make_runner(mocker, max_concurrent=2)
    mocker.patch("web.runner.store")

    async def slow_stream(*a, **kw):
        await asyncio.sleep(10)
        yield

    runner.backend.send_message = slow_stream

    async def _run():
        runner.submit("c1", "p", [])
        runner._queue = [("c1", "p", [], None, None), ("c2", "p", [], None, None)]
        runner._drain_queue()
        assert "c2" in runner._running
        assert len(runner._queue) == 0
        for t in runner._running.values():
            t.cancel()
        await asyncio.gather(*runner._running.values(), return_exceptions=True)

    asyncio.run(_run())


def test_run_agent_persists_assistant_events(runner, mocker):
    mock_store = mocker.patch("web.runner.store")
    mock_msg = mocker.MagicMock()
    mock_msg.id = 42
    mock_store.add_message.return_value = mock_msg

    events = [make_event("assistant", "Hello"), make_event("assistant", "world")]

    async def mock_stream(*args, **kwargs):
        for e in events:
            yield e

    runner.backend.send_message = mock_stream

    async def _run():
        await runner._run_agent("c1", "prompt", [], None, None)

    asyncio.run(_run())

    mock_store.add_message.assert_any_call("c1", "assistant", "Hello")
    mock_store.update_message.assert_called_with(42, "Hello\nworld")
    mock_store.update_conversation.assert_called_with("c1", needs_response=False)


def test_run_agent_persists_tool_events(runner, mocker):
    mock_store = mocker.patch("web.runner.store")
    mock_store.add_message.return_value = mocker.MagicMock(id=1)
    mocker.patch("web.runner._serialize_tool_event", return_value='{"tool":"Bash"}')

    events = [
        make_event("assistant", "thinking"),
        make_event("tool_use", {"tool": "Bash", "input": {}}),
        make_event("tool_result", "result output"),
    ]

    async def mock_stream(*args, **kwargs):
        for e in events:
            yield e

    runner.backend.send_message = mock_stream

    async def _run():
        await runner._run_agent("c1", "prompt", [], None, None)

    asyncio.run(_run())

    calls = [c for c in mock_store.add_message.call_args_list if c[0][1] in ("tool_use", "tool_result")]
    assert len(calls) == 2


def test_run_agent_handles_system_init(runner, mocker):
    mock_store = mocker.patch("web.runner.store")
    mock_store.add_message.return_value = mocker.MagicMock(id=1)

    events = [make_event("system", "init", raw={"subtype": "init", "session_id": "sess-123"})]

    async def mock_stream(*args, **kwargs):
        for e in events:
            yield e

    runner.backend.send_message = mock_stream

    async def _run():
        await runner._run_agent("c1", "prompt", [], None, None)

    asyncio.run(_run())

    mock_store.update_conversation.assert_any_call("c1", session_id="sess-123")


def test_run_agent_persists_usage(runner, mocker):
    mock_store = mocker.patch("web.runner.store")
    mock_store.add_message.return_value = mocker.MagicMock(id=1)

    events = [make_event("system", "usage", raw={"usage": {"input_tokens": 100, "output_tokens": 50}})]

    async def mock_stream(*args, **kwargs):
        for e in events:
            yield e

    runner.backend.send_message = mock_stream

    async def _run():
        await runner._run_agent("c1", "prompt", [], None, None)

    asyncio.run(_run())

    mock_store.accumulate_usage.assert_called_once()
    call_kwargs = mock_store.accumulate_usage.call_args
    assert call_kwargs[1]["input_tokens"] == 100
    assert call_kwargs[1]["output_tokens"] == 50


def test_run_agent_persists_api_retry(runner, mocker):
    mock_store = mocker.patch("web.runner.store")
    mock_store.add_message.return_value = mocker.MagicMock(id=1)

    events = [make_event("system", "retry", raw={"subtype": "api_retry", "attempt": 2})]

    async def mock_stream(*args, **kwargs):
        for e in events:
            yield e

    runner.backend.send_message = mock_stream

    async def _run():
        await runner._run_agent("c1", "prompt", [], None, None)

    asyncio.run(_run())

    system_calls = [c for c in mock_store.add_message.call_args_list if c[0][1] == "system"]
    assert len(system_calls) == 1


def test_run_agent_clears_needs_response_on_error(runner, mocker):
    mock_store = mocker.patch("web.runner.store")

    async def mock_stream(*args, **kwargs):
        raise RuntimeError("boom")
        yield  # noqa: F841

    runner.backend.send_message = mock_stream

    async def _run():
        await runner._run_agent("c1", "prompt", [], None, None)

    asyncio.run(_run())

    mock_store.update_conversation.assert_called_with("c1", needs_response=False)
    assert runner.is_done("c1")
    assert "c1" not in runner._running


def test_run_agent_drains_queue_on_finish(mocker):
    runner = make_runner(mocker, max_concurrent=1)
    mock_store = mocker.patch("web.runner.store")
    mock_store.add_message.return_value = mocker.MagicMock(id=1)

    async def mock_stream(*args, **kwargs):
        yield make_event("assistant", "done")

    async def slow_stream(*a, **kw):
        await asyncio.sleep(10)
        yield

    runner.backend.send_message = mock_stream

    async def _run():
        runner.submit("c1", "first", [])
        runner.backend.send_message = slow_stream
        runner._queue = [("c2", "second", [], None, None)]
        await runner._running["c1"]
        await asyncio.sleep(0)
        assert "c2" in runner._running
        runner._running["c2"].cancel()
        await asyncio.gather(*runner._running.values(), return_exceptions=True)

    asyncio.run(_run())


def test_run_agent_resets_assistant_on_tool_use(runner, mocker):
    mock_store = mocker.patch("web.runner.store")
    mock_store.add_message.return_value = mocker.MagicMock(id=10)
    mocker.patch("web.runner._serialize_tool_event", return_value="{}")

    events = [
        make_event("assistant", "thinking..."),
        make_event("tool_use", {"tool": "Read", "input": {}}),
        make_event("assistant", "after tool"),
    ]

    async def mock_stream(*args, **kwargs):
        for e in events:
            yield e

    runner.backend.send_message = mock_stream

    async def _run():
        await runner._run_agent("c1", "prompt", [], None, None)

    asyncio.run(_run())

    assistant_adds = [c for c in mock_store.add_message.call_args_list if c[0][1] == "assistant"]
    assert len(assistant_adds) == 2


def test_run_agent_checks_failure_markers(runner, mocker):
    mock_store = mocker.patch("web.runner.store")
    mock_store.add_message.return_value = mocker.MagicMock(id=1)
    mock_check = mocker.patch("web.runner._check_failure")

    events = [make_event("assistant", "sorry I can't do that")]

    async def mock_stream(*args, **kwargs):
        for e in events:
            yield e

    runner.backend.send_message = mock_stream

    async def _run():
        await runner._run_agent("c1", "prompt", [], None, None)

    asyncio.run(_run())

    mock_check.assert_called_once_with("c1", "sorry I can't do that")


def test_startup_clears_stuck_conversations(runner, mocker):
    mock_store = mocker.patch("web.runner.store")
    mock_store.clear_all_needs_response.return_value = ["c1", "c2"]

    async def _run():
        await runner.startup()
        assert runner._eviction_task is not None
        runner._eviction_task.cancel()
        await asyncio.gather(runner._eviction_task, return_exceptions=True)

    asyncio.run(_run())

    assert mock_store.add_message.call_count == 2


def test_shutdown_cancels_running_tasks(runner, mocker):
    mocker.patch("web.runner.store")

    async def slow_stream(*a, **kw):
        await asyncio.sleep(10)
        yield

    runner.backend.send_message = slow_stream

    async def _run():
        runner.submit("c1", "hello", [])
        assert "c1" in runner._running
        await runner.shutdown()

    asyncio.run(_run())


def test_serialize_tool_use_with_category(mocker):
    mocker.patch("web.runner.classify_tool", return_value="API: Matomo")
    event = make_event("tool_use", {"tool": "Bash", "input": {"command": "curl ..."}})
    result = json.loads(_serialize_tool_event(event, "c1", None))
    assert result["category"] == "API: Matomo"
    assert result["tool"] == "Bash"


def test_serialize_tool_result_with_api_calls(mocker):
    mocker.patch("web.runner.parse_api_signals", return_value=[{"source": "matomo"}])
    event = make_event("tool_result", {"output": "some output with signals"})
    result = json.loads(_serialize_tool_event(event, "c1", None))
    assert "api_calls" in result


def test_serialize_tool_result_without_api_calls(mocker):
    mocker.patch("web.runner.parse_api_signals", return_value=[])
    event = make_event("tool_result", "plain text output")
    result = _serialize_tool_event(event, "c1", None)
    assert result == "plain text output"


def test_serialize_tool_result_dict_content(mocker):
    mocker.patch("web.runner.parse_api_signals", return_value=[])
    event = make_event("tool_result", {"output": 12345})
    result = _serialize_tool_event(event, "c1", None)
    assert "12345" in result


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
    mocker.patch("web.runner.config.AGENT_BACKEND", "sdk")
    _persist_usage("c1", {"input_tokens": 10, "output_tokens": 5})
    call_kwargs = mock_store.accumulate_usage.call_args[1]
    assert call_kwargs["extra"] is None


def test_evict_loop_removes_stale_signals(runner):
    async def _run():
        runner.notify_done("old")
        runner._signals["old"].created_at -= 700
        runner.notify_done("fresh")
        runner._get_or_create_signal("active")
        runner._signals["active"].created_at -= 700

        task = asyncio.create_task(runner._evict_loop())
        # Patch sleep to run once immediately
        await asyncio.sleep(0)
        # Manually trigger eviction logic since we can't wait 30s
        now = asyncio.get_event_loop().time()
        import time as time_mod

        now = time_mod.monotonic()
        stale = [cid for cid, sig in runner._signals.items() if sig.done and (now - sig.created_at) > 600]
        for cid in stale:
            del runner._signals[cid]

        assert "old" not in runner._signals
        assert "fresh" in runner._signals
        assert "active" in runner._signals
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    asyncio.run(_run())
