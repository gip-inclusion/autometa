"""Task runner: distributed agent execution via Redis.

Each uvicorn worker runs a consumer loop that picks tasks from a shared Redis
list. SSE notifications use Redis pub/sub so any worker can serve any stream.
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field

import sentry_sdk
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from lib.api_signals import parse_api_signals
from lib.failure_detection import extract_snippet, find_failure_marker
from lib.tool_taxonomy import classify_tool

from . import alerts, config, session_sync
from .agents import get_agent
from .database import store
from .helpers import utcnow
from .otel import SpanStack, extract_trace_context, inject_trace_headers
from .redis_conn import get_redis
from .request_context import reset_conversation_id, set_conversation_id
from .sentry import set_user_context

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

PREFIX = "autometa"


@dataclass
class RunUsage:
    seen_ids: set[str] = field(default_factory=set)
    output_total: int = 0
    last_model: str | None = None


class TaskRunner:
    def __init__(self):
        self.backend = get_agent()
        self._running: dict[str, asyncio.Task] = {}
        self._cancel_tasks: dict[str, asyncio.Task] = {}
        self._worker_id = uuid.uuid4().hex[:12]
        self._consumer_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None
        self._sweep_task: asyncio.Task | None = None

    async def startup(self):
        r = await get_redis()
        await self._recover_stuck(r)
        self._consumer_task = asyncio.create_task(self._consumer_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._sweep_task = asyncio.create_task(self._sweep_loop())
        logger.info(
            "Task runner started (worker=%s, max_concurrent=%s)",
            self._worker_id,
            config.MAX_CONCURRENT_AGENTS,
        )

    async def shutdown(self):
        for task in (self._consumer_task, self._heartbeat_task, self._sweep_task):
            if task:
                task.cancel()
        for task in self._cancel_tasks.values():
            task.cancel()
        for task in self._running.values():
            task.cancel()
        if self._running:
            await asyncio.gather(*self._running.values(), return_exceptions=True)
        r = await get_redis()
        await r.delete(f"{PREFIX}:worker:{self._worker_id}")
        logger.info("Task runner stopped")

    async def submit(
        self,
        conv_id: str,
        prompt: str,
        history: list[dict],
        user_email: str | None = None,
        session_id: str | None = None,
    ):
        r = await get_redis()
        # Why: a prior cancel/run leaves done:{conv} (TTL 600s); clear it so the new run's
        # SSE stream doesn't see is_done()=True and close immediately.
        await r.delete(f"{PREFIX}:done:{conv_id}")
        payload = json.dumps({
            "conv_id": conv_id,
            "prompt": prompt,
            "history": history,
            "session_id": session_id,
            "user_email": user_email,
            "trace_headers": inject_trace_headers(),
        })
        await r.rpush(f"{PREFIX}:tasks", payload)

    async def cancel(self, conv_id: str) -> bool:
        r = await get_redis()
        # Why: clear needs_response before the up-to-5s backend.cancel so an immediate
        # resend doesn't race the in-flight cancel and get a 409 "already running".
        store.update_conversation(conv_id, needs_response=False)
        await r.publish(f"{PREFIX}:cancel:{conv_id}", "1")
        if conv_id in self._running:
            await self.backend.cancel(conv_id)
            self._running.pop(conv_id, None)
        store.add_message(conv_id, "assistant", "*Interrompu.*")
        await self._notify_done(conv_id)
        return True

    async def notify(self, conv_id: str):
        r = await get_redis()
        await r.publish(f"{PREFIX}:conv:{conv_id}", "update")

    async def notify_done(self, conv_id: str):
        await self._notify_done(conv_id)

    async def _notify_done(self, conv_id: str):
        r = await get_redis()
        await r.set(f"{PREFIX}:done:{conv_id}", "1", ex=600)
        await r.publish(f"{PREFIX}:conv:{conv_id}", "done")

    async def is_done(self, conv_id: str) -> bool:
        r = await get_redis()
        return await r.exists(f"{PREFIX}:done:{conv_id}") > 0

    async def cleanup(self, conv_id: str):
        r = await get_redis()
        await r.delete(f"{PREFIX}:done:{conv_id}")

    async def subscribe(self, conv_id: str):
        r = await get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(f"{PREFIX}:conv:{conv_id}")
        return pubsub

    async def _consumer_loop(self):
        r = await get_redis()
        while True:
            conv_id = None
            try:
                if len(self._running) >= config.MAX_CONCURRENT_AGENTS:
                    await asyncio.sleep(0.5)
                    continue
                result = await r.blpop(f"{PREFIX}:tasks", timeout=1)
                if result is None:
                    continue
                _, payload_str = result
                payload = json.loads(payload_str)
                conv_id = payload["conv_id"]
                if conv_id in self._running:
                    continue
                # Skip stale tasks (already handled or cancelled)
                conv = store.get_conversation(conv_id, include_messages=False)
                if not conv or not conv.needs_response:
                    continue
                await r.set(f"{PREFIX}:running:{conv_id}", self._worker_id, ex=300)
                sid = payload.get("session_id")
                if sid:
                    await asyncio.to_thread(session_sync.download_session, sid)
                history = history_for_turn(conv_id, sid, payload["history"])
                # Why: "sentry_trace" was the pre-OTel key. Keep one release for rolling deploys.
                trace_headers = payload.get("trace_headers") or payload.get("sentry_trace") or {}
                task = asyncio.create_task(
                    self._run_agent(
                        conv_id,
                        payload["prompt"],
                        history,
                        payload.get("user_email"),
                        trace_headers,
                        sid,
                    )
                )
                self._running[conv_id] = task
            except Exception:
                # Why: one bad task (DB/Redis blip, malformed payload) must never kill the loop
                # and strand every future conversation (silent consumer death, 2026-06-12 outage).
                logger.exception("consumer loop failed handling task (conv=%s)", conv_id)
                if conv_id:
                    try:
                        await self._release_conversation(r, conv_id, "*Une erreur s'est produite, merci de réessayer.*")
                    except Exception:
                        # Why: recovery hits the same DB/Redis that may still be down; never let it
                        # re-kill the loop. The periodic sweep reconciles this conversation later.
                        logger.exception("consumer recovery failed (conv=%s)", conv_id)
                await asyncio.sleep(0.5)

    async def _heartbeat_loop(self):
        r = await get_redis()
        while True:
            await r.set(f"{PREFIX}:worker:{self._worker_id}", "1", ex=30)
            for conv_id in list(self._running):
                await r.expire(f"{PREFIX}:running:{conv_id}", 300)
            await asyncio.sleep(10)

    async def _release_conversation(self, r, conv_id, note):
        """Un-stick a conversation: clear the running flag, tell the user, close the stream, drop the key."""
        store.update_conversation(conv_id, needs_response=False)
        store.add_message(conv_id, "assistant", note)
        await self.notify_done(conv_id)
        await r.delete(f"{PREFIX}:running:{conv_id}")

    async def _reconcile_stuck(self, r, min_age_seconds, note):
        stuck = store.get_running_conversation_ids(older_than_seconds=min_age_seconds)
        cleared = 0
        for conv_id in stuck:
            worker = await r.get(f"{PREFIX}:running:{conv_id}")
            if worker and await r.exists(f"{PREFIX}:worker:{worker}"):
                continue
            await self._release_conversation(r, conv_id, note)
            cleared += 1
        return cleared

    async def _recover_stuck(self, r):
        cleared = await self._reconcile_stuck(r, 0, "*Interrompu (redémarrage serveur).*")
        if cleared:
            logger.info("Cleared %s stuck conversations on startup", cleared)

    async def _sweep_loop(self):
        r = await get_redis()
        while True:
            # Why: reconciliation otherwise runs only at startup; a long-lived process that never
            # restarts accumulates zombies indefinitely. A live run is protected by the worker-key
            # check in _reconcile_stuck; the 15min age only guards convs queued but not yet picked up.
            await asyncio.sleep(60)
            try:
                cleared = await self._reconcile_stuck(r, 900, "*Interrompu.*")
                if cleared:
                    logger.info("Swept %s stuck conversations", cleared)
            except Exception:
                # Why: a sweep glitch (DB/Redis blip) must never kill the loop it runs in.
                logger.exception("stuck-conversation sweep failed")

    async def _listen_cancel(self, conv_id: str):
        r = await get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(f"{PREFIX}:cancel:{conv_id}")
        try:
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    await self.backend.cancel(conv_id)
                    break
        finally:
            await pubsub.unsubscribe()
            await pubsub.aclose()

    async def _run_agent(
        self,
        conversation_id: str,
        prompt: str,
        history: list[dict],
        user_email: str | None,
        trace_headers: dict | None = None,
        session_id: str | None = None,
    ):
        parent_ctx = extract_trace_context(trace_headers or {})

        my_task = asyncio.current_task()
        cancel_task = asyncio.create_task(self._listen_cancel(conversation_id))
        self._cancel_tasks[conversation_id] = cancel_task

        assistant_text_parts: list[str] = []
        assistant_msg_id: int | None = None
        all_assistant_texts: list[str] = []
        tool_spans = SpanStack()
        tool_call_count = 0
        tool_active_name: str | None = None
        tool_active_start: float | None = None
        agent_start = time.perf_counter()
        agent_status = "ok"
        run_usage = RunUsage()

        def _close_tool_log():
            nonlocal tool_active_name, tool_active_start
            if tool_active_name is None or tool_active_start is None:
                return
            duration_ms = round((time.perf_counter() - tool_active_start) * 1000, 2)
            logger.info(
                "agent.tool.completed",
                extra={
                    "tool.name": tool_active_name,
                    "tool.duration": duration_ms,
                    "session.id": conversation_id,
                },
            )
            tool_active_name = None
            tool_active_start = None

        with tracer.start_as_current_span(
            "agent.run",
            context=parent_ctx,
            attributes={"conversation_id": conversation_id, "agent_backend": config.AGENT_BACKEND},
        ) as span:
            if user_email:
                set_user_context(user_email)
            sentry_sdk.set_tag("agent_backend", config.AGENT_BACKEND)
            conv_token = set_conversation_id(conversation_id)

            try:
                async for event in self.backend.send_message(
                    conversation_id=conversation_id,
                    message=prompt,
                    history=history,
                    session_id=session_id,
                    user_email=user_email,
                ):
                    if event.type == "assistant":
                        assistant_text_parts.append(str(event.content))
                        append_mode = bool(getattr(event, "raw", {}).get("append"))
                        full_text = "".join(assistant_text_parts) if append_mode else "\n".join(assistant_text_parts)
                        if assistant_msg_id is None:
                            msg = store.add_message(conversation_id, "assistant", full_text)
                            assistant_msg_id = msg.id if msg else None
                        else:
                            store.update_message(assistant_msg_id, full_text)
                        _record_usage(conversation_id, event.raw, run_usage)
                        await self.notify(conversation_id)

                    elif event.type in ("tool_use", "tool_result"):
                        if event.type == "tool_use":
                            tool_call_count += 1
                            if config.TOOL_CALL_WARNING and tool_call_count == config.TOOL_CALL_WARNING:
                                logger.warning("Agent reached %d tool calls for %s", tool_call_count, conversation_id)
                            if config.MAX_TOOL_CALLS and tool_call_count >= config.MAX_TOOL_CALLS:
                                logger.warning(
                                    "Agent exceeded tool call budget (%d) for %s",
                                    config.MAX_TOOL_CALLS,
                                    conversation_id,
                                )
                                sentry_sdk.add_breadcrumb(
                                    message=f"Tool call budget exceeded: {tool_call_count}",
                                    category="agent",
                                    level="warning",
                                )
                                await self.backend.cancel(conversation_id)
                                store.add_message(
                                    conversation_id,
                                    "assistant",
                                    f"*Budget de {config.MAX_TOOL_CALLS} appels d'outils dépassé "
                                    "— arrêt automatique. Relancez avec une question plus ciblée.*",
                                )
                                await self.notify(conversation_id)
                                break
                            _close_tool_log()
                            tool_spans.pop()
                            tool_name = (
                                event.content.get("tool", "unknown") if isinstance(event.content, dict) else "unknown"
                            )
                            tool_spans.push(tracer, "agent.tool", {"tool.name": tool_name})
                            tool_active_name = tool_name
                            tool_active_start = time.perf_counter()
                            if assistant_text_parts:
                                all_assistant_texts.extend(assistant_text_parts)
                            assistant_msg_id = None
                            assistant_text_parts = []
                        elif event.type == "tool_result":
                            _close_tool_log()
                            tool_spans.pop()
                        content = _serialize_tool_event(event, conversation_id, user_email)
                        store.add_message(conversation_id, event.type, content)
                        await self.notify(conversation_id)

                    elif event.type == "system":
                        if event.raw.get("usage"):
                            _record_span_usage(event.raw["usage"])
                        if event.raw.get("subtype") == "api_retry":
                            store.add_message(conversation_id, "system", json.dumps(event.raw))
                            await self.notify(conversation_id)
                        if event.raw.get("type") == "result" and event.raw.get("usage"):
                            _record_thinking_tail(conversation_id, event.raw["usage"], run_usage)

                    elif event.type == "error":
                        store.add_message(
                            conversation_id,
                            "assistant",
                            f"*Une erreur est survenue côté agent : {str(event.content)[:500]}*",
                        )
                        await self.notify(conversation_id)
                        agent_status = "error"

                    # Why: raw holds the full CLI JSON event — can be MBs for tool results
                    event.raw = {}

                if assistant_text_parts:
                    all_assistant_texts.extend(assistant_text_parts)

                full_response = " ".join(all_assistant_texts)
                if full_response:
                    _check_failure(conversation_id, full_response)

                span.set_status(Status(StatusCode.OK))

            # Why: top-level agent error handler — must not crash the consumer loop.
            except Exception:
                logger.exception("Agent error for %s", conversation_id)
                span.set_status(Status(StatusCode.ERROR))
                sentry_sdk.capture_exception()
                agent_status = "error"
            finally:
                _close_tool_log()
                tool_spans.close_all()
                reset_conversation_id(conv_token)
                cancel_task.cancel()
                # Why: after a cancel+resend the slot may now hold a newer run for this conv;
                # only this run may clear its own state, never clobber the restart (slot is None
                # means cancel already took ownership, or a direct call with no consumer slot).
                slot = self._running.get(conversation_id)
                if slot is my_task or slot is None:
                    store.update_conversation(conversation_id, needs_response=False)
                    await self.notify_done(conversation_id)
                    self._running.pop(conversation_id, None)
                    r = await get_redis()
                    await r.delete(f"{PREFIX}:running:{conversation_id}")
                if self._cancel_tasks.get(conversation_id) is cancel_task:
                    self._cancel_tasks.pop(conversation_id, None)
                duration_ms = round((time.perf_counter() - agent_start) * 1000, 2)
                logger.info(
                    "agent.run.completed",
                    extra={
                        "session.id": conversation_id,
                        "agent.duration": duration_ms,
                        "agent.tool_calls": tool_call_count,
                        "agent.status": agent_status,
                    },
                )


def _serialize_tool_event(event, conversation_id: str, user_email: str | None) -> str:
    if event.type == "tool_use" and isinstance(event.content, dict):
        tool_name = event.content.get("tool", "")
        tool_input = event.content.get("input", {})
        category = classify_tool(tool_name, tool_input)
        return json.dumps({**event.content, "category": category})

    if event.type == "tool_result":
        if isinstance(event.content, dict) and "output" in event.content:
            raw_content = event.content["output"]
            if not isinstance(raw_content, str):
                raw_content = str(raw_content)
        elif isinstance(event.content, str):
            raw_content = event.content
        else:
            raw_content = str(event.content)

        api_calls = parse_api_signals(raw_content)
        if api_calls:
            return json.dumps({"output": event.content, "api_calls": api_calls})

    return json.dumps(event.content) if isinstance(event.content, dict) else str(event.content)


def _record_span_usage(usage: dict):
    span = trace.get_current_span()
    if not span.is_recording():
        return
    attrs = {
        "gen_ai.system": "anthropic",
        "gen_ai.usage.input_tokens": usage.get("input_tokens", 0),
        "gen_ai.usage.output_tokens": usage.get("output_tokens", 0),
        "gen_ai.usage.cache_read_tokens": usage.get("cache_read_input_tokens", 0),
        "gen_ai.usage.cache_creation_tokens": usage.get("cache_creation_input_tokens", 0),
    }
    if model := usage.get("model"):
        attrs["gen_ai.request.model"] = model
    span.set_attributes(attrs)


def _record_usage(conversation_id: str, raw_event: dict, run_usage: RunUsage) -> None:
    msg = raw_event.get("message") or {}
    usage = msg.get("usage")
    if not usage:
        return
    cli_message_id = msg.get("id")
    if cli_message_id and cli_message_id in run_usage.seen_ids:
        return
    if cli_message_id:
        run_usage.seen_ids.add(cli_message_id)

    model = msg.get("model")
    try:
        store.insert_usage_event(
            conversation_id=conversation_id,
            cli_message_id=cli_message_id,
            timestamp=utcnow(),
            model=model,
            backend=config.AGENT_BACKEND,
            usage=usage,
        )
        run_usage.output_total += usage.get("output_tokens", 0) or 0
        if model:
            run_usage.last_model = model
    except Exception:  # Why: usage capture is forensic — never crash the agent stream over a bad event
        logger.exception("Failed to record usage for %s", conversation_id)


def _record_thinking_tail(conversation_id: str, result_usage: dict, run_usage: RunUsage) -> None:
    total_output = result_usage.get("output_tokens", 0) or 0
    delta = total_output - run_usage.output_total
    if delta <= 0:
        return
    try:
        store.insert_usage_event(
            conversation_id=conversation_id,
            cli_message_id=None,
            timestamp=utcnow(),
            model=run_usage.last_model,
            backend=config.AGENT_BACKEND,
            usage={"output_tokens": delta, "service_tier": result_usage.get("service_tier")},
            kind="thinking",
        )
        run_usage.output_total += delta
    except Exception:  # Why: usage capture is forensic — never crash the agent stream over a bad event
        logger.exception("Failed to record thinking tail for %s", conversation_id)


def _check_failure(conversation_id: str, text: str):
    marker = find_failure_marker(text)
    if not marker:
        return
    snippet = extract_snippet(text, marker)
    conv = store.get_conversation(conversation_id)
    title = conv.title if conv and conv.title else "Sans titre"
    threading.Thread(target=_send_failure_notification, args=(conversation_id, title, snippet), daemon=True).start()


def _send_failure_notification(conv_id: str, title: str, snippet: str):
    url = f"{config.BASE_URL}/explorations/{conv_id}"
    message = (
        f":warning: *Erreur détectée dans une conversation*\n\n"
        f'<{url}|{title}> — "{snippet}"\n\n'
        f"_Vérifiez que la réponse est correcte._"
    )
    alerts.notify_alert_channel(message)


def history_for_turn(conv_id: str, session_id: str | None, default_history: list[dict]) -> list[dict]:
    """Seed history: empty when the session file is present (resume works), full transcript when it is missing."""
    if not session_id or session_sync.get_session_path(session_id).exists():
        return default_history

    logger.warning("Session file %s missing for %s — falling back to full history", session_id, conv_id)
    sentry_sdk.capture_message(
        f"Resume unavailable for conversation {conv_id}; using history fallback", level="warning"
    )

    conv = store.get_conversation(conv_id, include_messages=True)
    if not conv:
        return default_history

    msgs = [m for m in conv.messages if m.type in ("user", "assistant")]
    if msgs and msgs[-1].type == "user":
        msgs = msgs[:-1]
    return [{"role": m.type, "content": m.content} for m in msgs]


runner = TaskRunner()
