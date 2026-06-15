"""Tests for web/runner.py — Redis-based TaskRunner."""

import asyncio
import json

import fakeredis.aioredis
import pytest

from web import complexity
from web.agents.base import AgentMessage
from web.database import Message
from web.runner import (
    RunUsage,
    TaskRunner,
    _record_span_usage,
    _record_thinking_tail,
    _record_usage,
    _send_failure_notification,
    _serialize_tool_event,
)


async def _noop_stream(*args, **kwargs):
    return
    yield  # noqa: F841


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


def make_runner(mocker, fake_redis, max_concurrent=2):
    mock_backend = mocker.MagicMock()
    mock_backend.send_message = _noop_stream
    mock_backend.cancel = mocker.AsyncMock()
    mocker.patch("web.runner.get_agent", return_value=mock_backend)
    mocker.patch("web.runner.get_redis", return_value=fake_redis)
    mocker.patch("web.runner.config.MAX_CONCURRENT_AGENTS", max_concurrent)
    mocker.patch("web.runner.session_sync")
    r = TaskRunner()
    return r


def make_event(type, content, raw=None):
    return AgentMessage(type=type, content=content, raw=raw or {})


@pytest.fixture
def runner(mocker, fake_redis):
    return make_runner(mocker, fake_redis)


def test_submit_pushes_to_redis(runner, fake_redis):
    async def _run():
        await runner.submit("c1", "hello", [], session_id="sess-1")
        tasks = await fake_redis.lrange("autometa:tasks", 0, -1)
        assert len(tasks) == 1
        payload = json.loads(tasks[0])
        assert payload["conv_id"] == "c1"
        assert payload["prompt"] == "hello"
        assert payload["session_id"] == "sess-1"

    asyncio.run(_run())


def test_run_agent_forwards_user_email_to_backend(runner, mocker):
    captured = {}

    async def capturing_stream(**kwargs):
        captured.update(kwargs)
        return
        yield

    runner.backend.send_message = capturing_stream
    mocker.patch("web.runner.store")

    async def _run():
        await runner._run_agent("c1", "prompt", [], "alice@example.com", None)

    asyncio.run(_run())

    assert captured["conversation_id"] == "c1"
    assert captured["user_email"] == "alice@example.com"


def test_cancel_publishes_and_updates_db(runner, mocker):
    mock_store = mocker.patch("web.runner.store")

    async def _run():
        await runner.cancel("c1")
        mock_store.update_conversation.assert_called_with("c1", needs_response=False)
        mock_store.add_message.assert_called_with("c1", "assistant", "*Interrompu.*")

    asyncio.run(_run())


def test_cancel_clears_needs_response_before_backend_cancel_completes(runner, mocker):
    """Cancel must mark the conv stopped before the slow backend.cancel."""
    mock_store = mocker.patch("web.runner.store")
    backend_cancel_started = asyncio.Event()
    backend_cancel_may_finish = asyncio.Event()

    async def slow_backend_cancel(conv_id):
        backend_cancel_started.set()
        await backend_cancel_may_finish.wait()

    runner.backend.cancel = slow_backend_cancel
    runner._running["c1"] = mocker.MagicMock()

    async def _run():
        cancel_task = asyncio.create_task(runner.cancel("c1"))
        await backend_cancel_started.wait()
        cleared = any(c.kwargs.get("needs_response") is False for c in mock_store.update_conversation.call_args_list)
        backend_cancel_may_finish.set()
        await cancel_task
        assert cleared, "needs_response still True while backend.cancel runs -> immediate resend would 409"

    asyncio.run(_run())


def test_submit_clears_stale_done_key_from_previous_cancel(runner, fake_redis, mocker):
    """submit() must clear the done marker a prior cancel left behind."""
    mocker.patch("web.runner.store")

    async def _run():
        await runner.cancel("c1")
        assert await runner.is_done("c1")  # stale marker left by cancel (TTL 600s)
        await runner.submit("c1", "nouvelle question", [])
        assert not await runner.is_done("c1"), "new run must not inherit the previous cancel's done marker"

    asyncio.run(_run())


def test_finishing_old_run_does_not_evict_a_restarted_run(mocker, fake_redis):
    """An old run finishing must not clobber a same-conv restart."""
    runner = make_runner(mocker, fake_redis)
    mocker.patch("web.runner.store")

    old_can_finish = asyncio.Event()

    async def old_stream(**kwargs):
        await old_can_finish.wait()
        return
        yield  # noqa: F841

    async def new_stream(**kwargs):
        await asyncio.sleep(5)
        yield make_event("assistant", "x")

    async def _run():
        runner.backend.send_message = old_stream
        old_task = asyncio.create_task(runner._run_agent("c1", "old", [], None, None))
        runner._running["c1"] = old_task
        await asyncio.sleep(0.05)

        await runner.cancel("c1")
        assert "c1" not in runner._running

        runner.backend.send_message = new_stream
        new_task = asyncio.create_task(runner._run_agent("c1", "new", [], None, None))
        runner._running["c1"] = new_task
        await runner.cleanup("c1")
        await asyncio.sleep(0.05)
        assert runner._running.get("c1") is new_task

        old_can_finish.set()
        await asyncio.sleep(0.1)

        assert runner._running.get("c1") is new_task, "old run's finally evicted the restarted run"
        assert not await runner.is_done("c1"), "old run's finally marked the restarted run as done"

        new_task.cancel()
        old_task.cancel()
        await asyncio.gather(new_task, old_task, return_exceptions=True)

    asyncio.run(_run())


def test_run_agent_surfaces_backend_error_event(runner, mocker):
    """A backend 'error' event (CLI exit 1 on a dash prompt) must reach the user."""
    mock_store = mocker.patch("web.runner.store")
    mock_msg = mocker.MagicMock()
    mock_msg.id = 1
    mock_store.add_message.return_value = mock_msg

    async def err_stream(**kwargs):
        yield make_event("error", "Process exited with code 1: error: unknown option '- foo'")

    runner.backend.send_message = err_stream

    async def _run():
        await runner._run_agent("c1", "- foo", [], None, None)
        stored = [str(c.args) for c in mock_store.add_message.call_args_list]
        assert any("unknown option" in s for s in stored), "backend error event was dropped; user sees nothing"

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


def test_consumer_reads_legacy_sentry_trace_key_for_rolling_deploy(mocker, fake_redis):
    """In-flight Redis payloads queued before this PR use 'sentry_trace';
    the consumer must still extract them so traces aren't dropped during deploy."""
    runner = make_runner(mocker, fake_redis)
    mock_store = mocker.patch("web.runner.store")
    mock_conv = mocker.MagicMock()
    mock_conv.needs_response = True
    mock_store.get_conversation.return_value = mock_conv

    captured = {}

    async def fake_run_agent(*args, **kwargs):
        captured["trace_headers"] = args[4]

    mocker.patch.object(runner, "_run_agent", side_effect=fake_run_agent)

    async def _run():
        await fake_redis.rpush(
            "autometa:tasks",
            json.dumps({
                "conv_id": "c1",
                "prompt": "hi",
                "history": [],
                "sentry_trace": {"sentry-trace": "abc-1"},
            }),
        )
        consumer = asyncio.create_task(runner._consumer_loop())
        await asyncio.sleep(0.3)
        consumer.cancel()
        await asyncio.gather(consumer, return_exceptions=True)

    asyncio.run(_run())
    assert captured["trace_headers"] == {"sentry-trace": "abc-1"}


def test_consumer_prefers_new_trace_headers_key_over_legacy(mocker, fake_redis):
    runner = make_runner(mocker, fake_redis)
    mock_store = mocker.patch("web.runner.store")
    mock_conv = mocker.MagicMock()
    mock_conv.needs_response = True
    mock_store.get_conversation.return_value = mock_conv

    captured = {}

    async def fake_run_agent(*args, **kwargs):
        captured["trace_headers"] = args[4]

    mocker.patch.object(runner, "_run_agent", side_effect=fake_run_agent)

    async def _run():
        await fake_redis.rpush(
            "autometa:tasks",
            json.dumps({
                "conv_id": "c1",
                "prompt": "hi",
                "history": [],
                "trace_headers": {"sentry-trace": "new"},
                "sentry_trace": {"sentry-trace": "legacy"},
            }),
        )
        consumer = asyncio.create_task(runner._consumer_loop())
        await asyncio.sleep(0.3)
        consumer.cancel()
        await asyncio.gather(consumer, return_exceptions=True)

    asyncio.run(_run())
    assert captured["trace_headers"] == {"sentry-trace": "new"}


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


def test_consumer_survives_task_handling_exception(mocker, fake_redis):
    """A transient error on one task must not kill the loop; it must keep serving the next task."""
    runner = make_runner(mocker, fake_redis)
    mock_store = mocker.patch("web.runner.store")
    good_conv = mocker.MagicMock()
    good_conv.needs_response = True
    mock_store.get_conversation.side_effect = [RuntimeError("db connection lost"), good_conv]

    async def slow_stream(*a, **kw):
        await asyncio.sleep(10)
        yield

    runner.backend.send_message = slow_stream

    async def _run():
        for cid in ("boom", "good"):
            await fake_redis.rpush("autometa:tasks", json.dumps({"conv_id": cid, "prompt": "p", "history": []}))
        consumer = asyncio.create_task(runner._consumer_loop())
        await asyncio.sleep(1.0)
        assert "good" in runner._running, "consumer died on the first task's exception; the next task was never served"
        consumer.cancel()
        for t in runner._running.values():
            t.cancel()
        await asyncio.gather(consumer, *runner._running.values(), return_exceptions=True)

    asyncio.run(_run())


def test_consumer_survives_when_recovery_also_fails(mocker, fake_redis):
    """A sustained outage makes the recovery I/O fail too; the loop must still survive and serve the next task."""
    runner = make_runner(mocker, fake_redis)
    mock_store = mocker.patch("web.runner.store")
    good_conv = mocker.MagicMock()
    good_conv.needs_response = True
    mock_store.get_conversation.side_effect = [RuntimeError("db down"), good_conv]
    mock_store.update_conversation.side_effect = RuntimeError("db still down")

    async def slow_stream(*a, **kw):
        await asyncio.sleep(10)
        yield

    runner.backend.send_message = slow_stream

    async def _run():
        for cid in ("boom", "good"):
            await fake_redis.rpush("autometa:tasks", json.dumps({"conv_id": cid, "prompt": "p", "history": []}))
        consumer = asyncio.create_task(runner._consumer_loop())
        await asyncio.sleep(1.0)
        assert "good" in runner._running, "loop died when its own recovery I/O failed"
        consumer.cancel()
        for t in runner._running.values():
            t.cancel()
        await asyncio.gather(consumer, *runner._running.values(), return_exceptions=True)

    asyncio.run(_run())


def test_consumer_recovers_and_notifies_on_setup_failure(mocker, fake_redis):
    """A task erroring mid-setup is un-stuck (needs_response + running key), the user is told, the stream closes."""
    runner = make_runner(mocker, fake_redis)
    mock_store = mocker.patch("web.runner.store")
    conv = mocker.MagicMock()
    conv.needs_response = True
    mock_store.get_conversation.return_value = conv
    sess = mocker.patch("web.runner.session_sync")
    sess.download_session.side_effect = RuntimeError("s3 unreachable")

    async def _run():
        await fake_redis.rpush(
            "autometa:tasks", json.dumps({"conv_id": "boom", "prompt": "p", "history": [], "session_id": "s1"})
        )
        consumer = asyncio.create_task(runner._consumer_loop())
        await asyncio.sleep(0.3)
        consumer.cancel()
        await asyncio.gather(consumer, return_exceptions=True)
        mock_store.update_conversation.assert_any_call("boom", needs_response=False)
        assert not await fake_redis.exists("autometa:running:boom"), "running key left behind for the failed conv"
        assert any(
            c.args[0] == "boom" and c.args[1] == "assistant" and "erreur" in c.args[2].lower()
            for c in mock_store.add_message.call_args_list
        ), "no error message was shown to the user"
        assert await runner.is_done("boom"), "stream never closed; client waits forever"

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


def test_reconcile_clears_aged_stuck_conversations(mocker, fake_redis):
    """Periodic reconcile must query with the age threshold (race protection) and clear dead-worker convs."""
    runner = make_runner(mocker, fake_redis)
    mock_store = mocker.patch("web.runner.store")
    mock_store.get_running_conversation_ids.return_value = ["zombie"]

    async def _run():
        cleared = await runner._reconcile_stuck(fake_redis, min_age_seconds=300, note="*Interrompu.*")
        mock_store.get_running_conversation_ids.assert_called_once_with(older_than_seconds=300)
        mock_store.update_conversation.assert_called_once_with("zombie", needs_response=False)
        mock_store.add_message.assert_called_once_with("zombie", "assistant", "*Interrompu.*")
        assert await runner.is_done("zombie"), "swept conv's SSE stream was never closed"
        assert cleared == 1

    asyncio.run(_run())


def test_reconcile_skips_conversation_with_live_worker(mocker, fake_redis):
    """A conversation genuinely running on a live worker must never be cleared by reconcile."""
    runner = make_runner(mocker, fake_redis)
    mock_store = mocker.patch("web.runner.store")
    mock_store.get_running_conversation_ids.return_value = ["live"]

    async def _run():
        await fake_redis.set("autometa:running:live", "w1")
        await fake_redis.set("autometa:worker:w1", "1")
        cleared = await runner._reconcile_stuck(fake_redis, min_age_seconds=300, note="*x*")
        mock_store.update_conversation.assert_not_called()
        assert cleared == 0

    asyncio.run(_run())


def test_reconcile_skips_queued_conversation(mocker, fake_redis):
    """A stuck conv whose task is still queued is waiting for a slot, not orphaned — keep it."""
    runner = make_runner(mocker, fake_redis)
    mock_store = mocker.patch("web.runner.store")
    mock_store.get_running_conversation_ids.return_value = ["waiting"]

    async def _run():
        await fake_redis.rpush("autometa:tasks", json.dumps({"conv_id": "waiting", "prompt": "p", "history": []}))
        cleared = await runner._reconcile_stuck(fake_redis, min_age_seconds=900, note="*x*", skip_queued=True)
        mock_store.update_conversation.assert_not_called()
        assert cleared == 0

    asyncio.run(_run())


def test_heartbeat_survives_redis_error(mocker, fake_redis):
    """A Redis blip must not kill the heartbeat — reconcile liveness and the sweep depend on it."""
    runner = make_runner(mocker, fake_redis)
    mocker.patch.object(fake_redis, "set", side_effect=RuntimeError("redis blip"))

    async def _run():
        hb = asyncio.create_task(runner._heartbeat_loop())
        await asyncio.sleep(0.2)
        assert not hb.done(), "heartbeat loop died on a Redis error"
        hb.cancel()
        await asyncio.gather(hb, return_exceptions=True)

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


def _usage_raw_event(msg_id, model, usage):
    return {"message": {"id": msg_id, "model": model, "usage": usage}}


def test_record_usage_inserts_event(mocker):
    mock_store = mocker.patch("web.runner.store")
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    state = RunUsage()
    raw = _usage_raw_event(
        "msg_abc",
        "claude-sonnet-4-7",
        {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_creation_input_tokens": 200,
            "cache_read_input_tokens": 300,
            "service_tier": "priority",
        },
    )

    _record_usage("c1", raw, state)

    assert "msg_abc" in state.seen_ids
    assert state.output_total == 50
    assert state.last_model == "claude-sonnet-4-7"
    insert_kwargs = mock_store.insert_usage_event.call_args[1]
    assert insert_kwargs["conversation_id"] == "c1"
    assert insert_kwargs["cli_message_id"] == "msg_abc"
    assert insert_kwargs["model"] == "claude-sonnet-4-7"
    assert insert_kwargs["backend"] == "cli"
    assert insert_kwargs["usage"]["input_tokens"] == 100
    assert insert_kwargs["usage"]["output_tokens"] == 50


def test_record_usage_dedups_same_message_id(mocker):
    mock_store = mocker.patch("web.runner.store")
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    state = RunUsage()
    raw = _usage_raw_event("msg_dup", "claude-sonnet-4-7", {"input_tokens": 10, "output_tokens": 5})

    _record_usage("c1", raw, state)
    _record_usage("c1", raw, state)

    assert mock_store.insert_usage_event.call_count == 1
    assert state.output_total == 5


def test_record_usage_noop_when_usage_missing(mocker):
    mock_store = mocker.patch("web.runner.store")
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    state = RunUsage()

    _record_usage("c1", {"message": {"id": "msg_x", "model": "m"}}, state)

    assert mock_store.insert_usage_event.call_count == 0
    assert state.output_total == 0


def test_record_usage_leaves_state_unchanged_on_store_failure(mocker):
    mock_store = mocker.patch("web.runner.store")
    mock_store.insert_usage_event.side_effect = RuntimeError("db is down")
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    state = RunUsage()
    raw = _usage_raw_event("msg_boom", "claude-sonnet-4-7", {"input_tokens": 1, "output_tokens": 42})

    _record_usage("c1", raw, state)

    assert "msg_boom" in state.seen_ids
    assert state.output_total == 0
    assert state.last_model is None


def test_record_thinking_tail_writes_delta(mocker):
    mock_store = mocker.patch("web.runner.store")
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    state = RunUsage(output_total=141, last_model="claude-opus-4-7")

    _record_thinking_tail("c1", {"output_tokens": 1717, "service_tier": "standard"}, state)

    insert_kwargs = mock_store.insert_usage_event.call_args[1]
    assert insert_kwargs["kind"] == "thinking"
    assert insert_kwargs["model"] == "claude-opus-4-7"
    assert insert_kwargs["cli_message_id"] is None
    assert insert_kwargs["usage"]["output_tokens"] == 1576
    assert state.output_total == 1717


@pytest.mark.parametrize("total,recorded", [(50, 50), (50, 70), (0, 0)])
def test_record_thinking_tail_skips_when_no_delta(mocker, total, recorded):
    mock_store = mocker.patch("web.runner.store")
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    state = RunUsage(output_total=recorded, last_model="claude-sonnet-4-7")

    _record_thinking_tail("c1", {"output_tokens": total}, state)

    assert mock_store.insert_usage_event.call_count == 0


def test_record_thinking_tail_leaves_state_unchanged_on_store_failure(mocker):
    mock_store = mocker.patch("web.runner.store")
    mock_store.insert_usage_event.side_effect = RuntimeError("db is down")
    mocker.patch("web.runner.config.AGENT_BACKEND", "cli")
    state = RunUsage(output_total=10, last_model="claude-opus-4-7")

    _record_thinking_tail("c1", {"output_tokens": 1000}, state)

    assert state.output_total == 10


def test_record_span_usage_sets_gen_ai_attributes_on_active_span():
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("test")

    with tracer.start_as_current_span("agent.run"):
        _record_span_usage(
            {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_read_input_tokens": 30,
                "cache_creation_input_tokens": 10,
                "model": "claude-opus-4-7",
            },
        )

    span = exporter.get_finished_spans()[0]
    assert span.attributes["gen_ai.system"] == "anthropic"
    assert span.attributes["gen_ai.usage.input_tokens"] == 100
    assert span.attributes["gen_ai.usage.output_tokens"] == 50
    assert span.attributes["gen_ai.usage.cache_read_tokens"] == 30
    assert span.attributes["gen_ai.usage.cache_creation_tokens"] == 10
    assert span.attributes["gen_ai.request.model"] == "claude-opus-4-7"


def test_tool_span_is_current_between_tool_use_and_tool_result(mocker, fake_redis):
    """Sub-spans created during tool execution must inherit agent.tool as parent —
    proving the runner activates agent.tool via context.attach."""
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    mocker.patch("web.runner.tracer", trace.get_tracer("web.runner"))
    mocker.patch("web.runner.store")

    inner_tracer = trace.get_tracer("inner")
    inner_parent_ids: list[int] = []

    async def stream(**kwargs):
        yield make_event("tool_use", {"tool": "matomo"})
        with inner_tracer.start_as_current_span("inner_work") as inner:
            inner_parent_ids.append(inner.parent.span_id if inner.parent else 0)
        yield make_event("tool_result", {"output": "ok"})

    runner = make_runner(mocker, fake_redis)
    runner.backend.send_message = stream

    asyncio.run(runner._run_agent("c1", "p", [], None, None))

    spans_by_name = {s.name: s for s in exporter.get_finished_spans()}
    tool_span_id = spans_by_name["agent.tool"].context.span_id
    assert inner_parent_ids == [tool_span_id], (
        "inner span should be parented by agent.tool — meaning agent.tool was current"
    )


def test_run_agent_tool_call_budget_exceeded(mocker, fake_redis):
    runner = make_runner(mocker, fake_redis)
    mocker.patch("web.runner.config.MAX_TOOL_CALLS", 3)
    mocker.patch("web.runner.config.TOOL_CALL_WARNING", 2)
    mock_store = mocker.patch("web.runner.store")
    mock_msg = mocker.MagicMock()
    mock_msg.id = 1
    mock_store.add_message.return_value = mock_msg

    events = []
    for i in range(10):
        events.append(make_event("tool_use", {"tool": "Bash", "input": {"command": f"echo {i}"}}))
        events.append(make_event("tool_result", {"tool": "Bash", "output": f"result {i}"}))
    events.append(make_event("assistant", "Done"))

    async def mock_stream(*args, **kwargs):
        for e in events:
            yield e

    runner.backend.send_message = mock_stream

    async def _run():
        await runner._run_agent("c1", "prompt", [], None, None)
        # The budget message should have been stored
        budget_calls = [
            call
            for call in mock_store.add_message.call_args_list
            if len(call.args) >= 3 and call.args[1] == "assistant" and "Budget" in str(call.args[2])
        ]
        assert len(budget_calls) == 1
        assert "200" not in budget_calls[0].args[2]  # should use the mocked value 3
        assert "3" in budget_calls[0].args[2]

    asyncio.run(_run())


def test_run_agent_no_budget_when_disabled(mocker, fake_redis):
    runner = make_runner(mocker, fake_redis)
    mocker.patch("web.runner.config.MAX_TOOL_CALLS", 0)
    mocker.patch("web.runner.config.TOOL_CALL_WARNING", 0)
    mock_store = mocker.patch("web.runner.store")
    mock_msg = mocker.MagicMock()
    mock_msg.id = 1
    mock_store.add_message.return_value = mock_msg

    events = [
        make_event("tool_use", {"tool": "Bash", "input": {"command": "echo 1"}}),
        make_event("tool_result", {"tool": "Bash", "output": "1"}),
        make_event("assistant", "Done"),
    ]

    async def mock_stream(*args, **kwargs):
        for e in events:
            yield e

    runner.backend.send_message = mock_stream

    async def _run():
        await runner._run_agent("c1", "prompt", [], None, None)
        budget_calls = [
            call
            for call in mock_store.add_message.call_args_list
            if len(call.args) >= 3 and "Budget" in str(call.args[2])
        ]
        assert len(budget_calls) == 0

    asyncio.run(_run())


def test_send_failure_notification_delegates_to_alert_helper(mocker):
    notify = mocker.patch("web.runner.alerts.notify_alert_channel")

    _send_failure_notification("conv-1", "Ma conversation", "boom")

    notify.assert_called_once()
    message = notify.call_args[0][0]
    assert "conv-1" in message
    assert "Ma conversation" in message
    assert "boom" in message


def test_run_agent_emits_completion_log(runner, mocker, caplog):
    import logging

    mocker.patch("web.runner.store")

    with caplog.at_level(logging.INFO, logger="web.runner"):
        asyncio.run(runner._run_agent("c1", "prompt", [], None, None))

    matches = [r for r in caplog.records if r.message == "agent.run.completed"]
    assert len(matches) == 1
    record = matches[0]
    assert getattr(record, "session.id") == "c1"
    assert getattr(record, "agent.tool_calls") == 0
    assert getattr(record, "agent.status") == "ok"
    assert isinstance(getattr(record, "agent.duration"), float)


def test_run_agent_emits_tool_completion_log(runner, mocker, caplog):
    import logging

    async def tool_stream(**kwargs):
        yield make_event("tool_use", {"tool": "bash"})
        yield make_event("tool_result", {"result": "ok"})

    runner.backend.send_message = tool_stream
    mocker.patch("web.runner.store")

    with caplog.at_level(logging.INFO, logger="web.runner"):
        asyncio.run(runner._run_agent("c1", "prompt", [], None, None))

    tool_logs = [r for r in caplog.records if r.message == "agent.tool.completed"]
    assert len(tool_logs) == 1
    record = tool_logs[0]
    assert getattr(record, "tool.name") == "bash"
    assert getattr(record, "session.id") == "c1"
    assert isinstance(getattr(record, "tool.duration"), float)

    run_logs = [r for r in caplog.records if r.message == "agent.run.completed"]
    assert len(run_logs) == 1
    assert getattr(run_logs[0], "agent.tool_calls") == 1


def test_run_agent_emits_error_status_on_exception(runner, mocker, caplog):
    import logging

    async def failing_stream(**kwargs):
        raise RuntimeError("boom")
        yield  # noqa: F841

    runner.backend.send_message = failing_stream
    mocker.patch("web.runner.store")

    with caplog.at_level(logging.INFO, logger="web.runner"):
        asyncio.run(runner._run_agent("c1", "prompt", [], None, None))

    matches = [r for r in caplog.records if r.message == "agent.run.completed"]
    assert len(matches) == 1
    assert getattr(matches[0], "agent.status") == "error"


def _complex_messages(n=41):
    return [Message(type="user", content="q") for _ in range(n)]


def test_maybe_alert_complexity_injects_once_when_complex(runner, mocker):
    mock_store = mocker.patch("web.runner.store")
    conv = mocker.MagicMock()
    conv.messages = _complex_messages()
    mock_store.get_conversation.return_value = conv

    asyncio.run(runner._maybe_alert_complexity("c1"))

    mock_store.add_message.assert_called_once_with("c1", "assistant", complexity.ALERT_MESSAGE)


def test_maybe_alert_complexity_skips_when_already_alerted(runner, mocker):
    mock_store = mocker.patch("web.runner.store")
    conv = mocker.MagicMock()
    conv.messages = _complex_messages() + [Message(type="assistant", content=complexity.ALERT_MESSAGE)]
    mock_store.get_conversation.return_value = conv

    asyncio.run(runner._maybe_alert_complexity("c1"))

    mock_store.add_message.assert_not_called()


def test_maybe_alert_complexity_skips_when_simple(runner, mocker):
    mock_store = mocker.patch("web.runner.store")
    conv = mocker.MagicMock()
    conv.messages = [Message(type="user", content="q")]
    mock_store.get_conversation.return_value = conv

    asyncio.run(runner._maybe_alert_complexity("c1"))

    mock_store.add_message.assert_not_called()
