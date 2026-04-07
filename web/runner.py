"""Task runner: distributed agent execution via Redis.

Each uvicorn worker runs a consumer loop that picks tasks from a shared Redis
list. SSE notifications use Redis pub/sub so any worker can serve any stream.
"""

import asyncio
import json
import logging
import threading
import uuid

import sentry_sdk

from lib.api_signals import parse_api_signals
from lib.failure_detection import extract_snippet, find_failure_marker
from lib.tool_taxonomy import classify_tool

from . import config
from .agents import get_agent
from .database import store
from .redis_conn import get_redis
from .sentry import continue_trace, get_trace_headers, set_conversation_context, set_user_context

logger = logging.getLogger(__name__)

PREFIX = "autometa"


class TaskRunner:
    def __init__(self):
        self.backend = get_agent()
        self._running: dict[str, asyncio.Task] = {}
        self._cancel_tasks: dict[str, asyncio.Task] = {}
        self._worker_id = uuid.uuid4().hex[:12]
        self._consumer_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None

    async def startup(self):
        r = await get_redis()
        await self._recover_stuck(r)
        self._consumer_task = asyncio.create_task(self._consumer_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"Task runner started (worker={self._worker_id}, max_concurrent={config.MAX_CONCURRENT_AGENTS})")

    async def shutdown(self):
        for task in (self._consumer_task, self._heartbeat_task):
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
    ):
        r = await get_redis()
        payload = json.dumps({
            "conv_id": conv_id,
            "prompt": prompt,
            "history": history,
            "user_email": user_email,
            "sentry_trace": get_trace_headers(),
        })
        await r.rpush(f"{PREFIX}:tasks", payload)

    async def cancel(self, conv_id: str) -> bool:
        r = await get_redis()
        await r.publish(f"{PREFIX}:cancel:{conv_id}", "1")
        if conv_id in self._running:
            await self.backend.cancel(conv_id)
            self._running.pop(conv_id, None)
        store.update_conversation(conv_id, needs_response=False)
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
            task = asyncio.create_task(
                self._run_agent(
                    conv_id,
                    payload["prompt"],
                    payload["history"],
                    payload.get("user_email"),
                    payload.get("sentry_trace", {}),
                )
            )
            self._running[conv_id] = task

    async def _heartbeat_loop(self):
        r = await get_redis()
        while True:
            await r.set(f"{PREFIX}:worker:{self._worker_id}", "1", ex=30)
            for conv_id in list(self._running):
                await r.expire(f"{PREFIX}:running:{conv_id}", 300)
            await asyncio.sleep(10)

    async def _recover_stuck(self, r):
        stuck = store.get_running_conversation_ids()
        cleared = 0
        for conv_id in stuck:
            worker = await r.get(f"{PREFIX}:running:{conv_id}")
            if worker and await r.exists(f"{PREFIX}:worker:{worker}"):
                continue
            store.update_conversation(conv_id, needs_response=False)
            store.add_message(conv_id, "assistant", "*Interrompu (redémarrage serveur).*")
            await r.delete(f"{PREFIX}:running:{conv_id}")
            cleared += 1
        if cleared:
            logger.info(f"Cleared {cleared} stuck conversations on startup")

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
        sentry_trace: dict | None = None,
    ):
        # Continue the Sentry trace from the HTTP request that submitted this task
        continue_trace(sentry_trace or {})

        cancel_task = asyncio.create_task(self._listen_cancel(conversation_id))
        self._cancel_tasks[conversation_id] = cancel_task

        assistant_text_parts: list[str] = []
        assistant_msg_id: int | None = None
        all_assistant_texts: list[str] = []
        tool_span = None
        tool_call_count = 0

        with sentry_sdk.start_transaction(op="agent.run", name=f"agent {config.AGENT_BACKEND}") as txn:
            txn.set_tag("conversation_id", conversation_id)
            txn.set_tag("agent_backend", config.AGENT_BACKEND)
            if user_email:
                set_user_context(user_email)
            set_conversation_context(conversation_id, config.AGENT_BACKEND)

            try:
                async for event in self.backend.send_message(
                    conversation_id=conversation_id,
                    message=prompt,
                    history=history,
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
                            if tool_span:
                                tool_span.finish()
                            tool_name = (
                                event.content.get("tool", "unknown") if isinstance(event.content, dict) else "unknown"
                            )
                            tool_span = sentry_sdk.start_span(op="agent.tool", name=tool_name)
                            if assistant_text_parts:
                                all_assistant_texts.extend(assistant_text_parts)
                            assistant_msg_id = None
                            assistant_text_parts = []
                        elif event.type == "tool_result" and tool_span:
                            tool_span.finish()
                            tool_span = None
                        content = _serialize_tool_event(event, conversation_id, user_email)
                        store.add_message(conversation_id, event.type, content)
                        await self.notify(conversation_id)

                    elif event.type == "system":
                        if event.raw.get("usage"):
                            _persist_usage(conversation_id, event.raw["usage"])
                        if event.raw.get("subtype") == "api_retry":
                            store.add_message(conversation_id, "system", json.dumps(event.raw))
                            await self.notify(conversation_id)

                    # Why: raw holds the full CLI JSON event — can be MBs for tool results
                    event.raw = {}

                if tool_span:
                    tool_span.finish()
                    tool_span = None

                if assistant_text_parts:
                    all_assistant_texts.extend(assistant_text_parts)

                full_response = " ".join(all_assistant_texts)
                if full_response:
                    _check_failure(conversation_id, full_response)

                txn.set_status("ok")

            # Why: top-level agent error handler — must not crash the consumer loop.
            except Exception:
                logger.exception(f"Agent error for {conversation_id}")
                txn.set_status("internal_error")
                sentry_sdk.capture_exception()
            finally:
                if tool_span:
                    tool_span.finish()
                store.update_conversation(conversation_id, needs_response=False)
                await self.notify_done(conversation_id)
                self._running.pop(conversation_id, None)
                cancel_task.cancel()
                self._cancel_tasks.pop(conversation_id, None)
                r = await get_redis()
                await r.delete(f"{PREFIX}:running:{conversation_id}")
                logger.info(f"Agent finished for {conversation_id}")


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


def _persist_usage(conversation_id: str, usage: dict):
    extra = {}
    if usage.get("service_tier"):
        extra["service_tier"] = usage["service_tier"]
    if usage.get("web_search_requests"):
        extra["web_search_requests"] = usage["web_search_requests"]

    store.accumulate_usage(
        conversation_id,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
        cache_read_tokens=usage.get("cache_read_input_tokens", 0),
        backend=config.AGENT_BACKEND,
        extra=extra if extra else None,
    )


def _check_failure(conversation_id: str, text: str):
    marker = find_failure_marker(text)
    if not marker:
        return
    snippet = extract_snippet(text, marker)
    conv = store.get_conversation(conversation_id)
    title = conv.title if conv and conv.title else "Sans titre"
    threading.Thread(target=_send_failure_notification, args=(conversation_id, title, snippet), daemon=True).start()


def _send_failure_notification(conv_id: str, title: str, snippet: str):
    if not config.FAILURE_NOTIFY_EMAILS:
        return
    token = config.SLACK_BOT_TOKEN
    if not token:
        return

    from lib.slack import lookup_user, send_dm

    url = f"{config.BASE_URL}/explorations/{conv_id}"
    message = (
        f":warning: *Erreur détectée dans une conversation*\n\n"
        f'<{url}|{title}> — "{snippet}"\n\n'
        f"_Vérifiez que la réponse est correcte._"
    )

    for email in config.FAILURE_NOTIFY_EMAILS:
        try:
            slack_id = lookup_user(token, email)
            if not slack_id:
                logger.warning(f"Slack user not found for {email}")
                continue
            if send_dm(token, slack_id, message):
                logger.info(f"Failure notification sent to {email} for conversation {conv_id}")
            else:
                logger.warning(f"Failed to send Slack DM to {email}")
        # Why: runs in a background daemon thread, must not crash on transient Slack errors.
        except Exception:
            logger.exception(f"Error sending failure notification to {email}")


runner = TaskRunner()
