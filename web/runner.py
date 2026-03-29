"""Task runner: runs agent tasks and notifies SSE handlers.

Replaces the former ProcessManager + SignalRegistry. Tasks are submitted
directly (no DB polling) and notifications use in-memory asyncio.Events.
"""

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass, field

from lib.api_signals import parse_api_signals
from lib.failure_detection import extract_snippet, find_failure_marker
from lib.tool_taxonomy import classify_tool

from . import config
from .agents import get_agent
from .database import store

logger = logging.getLogger(__name__)


@dataclass
class _Signal:
    event: asyncio.Event = field(default_factory=asyncio.Event)
    done: bool = False
    counter: int = 0
    created_at: float = field(default_factory=time.monotonic)


class TaskRunner:
    def __init__(self):
        self.backend = get_agent()
        self._running: dict[str, asyncio.Task] = {}
        self._queue: list[tuple] = []
        self._signals: dict[str, _Signal] = {}
        self._eviction_task: asyncio.Task | None = None

    async def startup(self):
        cleared = await asyncio.to_thread(store.clear_all_needs_response)
        if cleared:
            for conv_id in cleared:
                store.add_message(conv_id, "assistant", "*Interrompu (redémarrage serveur).*")
            logger.info(f"Cleared {len(cleared)} stuck conversations on startup")
        self._eviction_task = asyncio.create_task(self._evict_loop())
        logger.info(f"Task runner started (max_concurrent={config.MAX_CONCURRENT_AGENTS})")

    async def shutdown(self):
        if self._eviction_task:
            self._eviction_task.cancel()
        for task in self._running.values():
            task.cancel()
        if self._running:
            await asyncio.gather(*self._running.values(), return_exceptions=True)
        logger.info("Task runner stopped")

    def submit(
        self,
        conv_id: str,
        prompt: str,
        history: list[dict],
        session_id: str | None = None,
        user_email: str | None = None,
    ):
        payload = (conv_id, prompt, history, session_id, user_email)
        if conv_id in self._running:
            logger.warning(f"Task already running for {conv_id}, ignoring")
            return
        if len(self._running) < config.MAX_CONCURRENT_AGENTS:
            self._start(payload)
        else:
            logger.info(f"Task queued for {conv_id} ({len(self._running)} running, {len(self._queue)} queued)")
            self._queue.append(payload)

    async def cancel(self, conv_id: str) -> bool:
        self._queue = [p for p in self._queue if p[0] != conv_id]
        if conv_id in self._running:
            await self.backend.cancel(conv_id)
            self._running.pop(conv_id, None)
        store.update_conversation(conv_id, needs_response=False)
        store.add_message(conv_id, "assistant", "*Interrompu.*")
        self.notify_done(conv_id)
        return True

    def is_running(self, conv_id: str) -> bool:
        task = self._running.get(conv_id)
        return task is not None and not task.done()

    def notify(self, conv_id: str):
        sig = self._signals.get(conv_id)
        if sig is None:
            return
        sig.counter += 1
        sig.event.set()

    def notify_done(self, conv_id: str):
        sig = self._get_or_create_signal(conv_id)
        sig.done = True
        sig.counter += 1
        sig.event.set()

    async def wait_for_update(self, conv_id: str, timeout: float = 3.0) -> bool:
        sig = self._get_or_create_signal(conv_id)
        counter_before = sig.counter
        try:
            await asyncio.wait_for(sig.event.wait(), timeout=timeout)
            sig.event.clear()
            return True
        except asyncio.TimeoutError:
            return sig.counter > counter_before

    def is_done(self, conv_id: str) -> bool:
        sig = self._signals.get(conv_id)
        return sig is not None and sig.done

    def cleanup(self, conv_id: str):
        self._signals.pop(conv_id, None)

    def _get_or_create_signal(self, conv_id: str) -> _Signal:
        if conv_id not in self._signals:
            self._signals[conv_id] = _Signal()
        return self._signals[conv_id]

    def _start(self, payload: tuple):
        conv_id = payload[0]
        task = asyncio.create_task(self._run_agent(*payload))
        self._running[conv_id] = task

    def _drain_queue(self):
        while self._queue and len(self._running) < config.MAX_CONCURRENT_AGENTS:
            payload = self._queue.pop(0)
            if payload[0] not in self._running:
                logger.info(f"Starting queued task for {payload[0]}")
                self._start(payload)

    async def _run_agent(
        self, conversation_id: str, prompt: str, history: list[dict], session_id: str | None, user_email: str | None
    ):
        assistant_text_parts: list[str] = []
        assistant_msg_id: int | None = None
        all_assistant_texts: list[str] = []

        try:
            async for event in self.backend.send_message(
                conversation_id=conversation_id,
                message=prompt,
                history=history,
                session_id=session_id,
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
                    self.notify(conversation_id)

                elif event.type in ("tool_use", "tool_result"):
                    if event.type == "tool_use":
                        if assistant_text_parts:
                            all_assistant_texts.extend(assistant_text_parts)
                        assistant_msg_id = None
                        assistant_text_parts = []
                    content = _serialize_tool_event(event, conversation_id, user_email)
                    store.add_message(conversation_id, event.type, content)
                    self.notify(conversation_id)

                elif event.type == "system":
                    if event.raw.get("subtype") == "init":
                        new_session_id = event.raw.get("session_id")
                        if new_session_id:
                            store.update_conversation(conversation_id, session_id=new_session_id)
                    if event.raw.get("usage"):
                        _persist_usage(conversation_id, event.raw["usage"])
                    if event.raw.get("subtype") == "api_retry":
                        store.add_message(conversation_id, "system", json.dumps(event.raw))
                        self.notify(conversation_id)

            if assistant_text_parts:
                all_assistant_texts.extend(assistant_text_parts)

            full_response = " ".join(all_assistant_texts)
            if full_response:
                _check_failure(conversation_id, full_response)

        # Why: top-level agent error handler — must not crash the task runner event loop.
        except Exception:
            logger.exception(f"Agent error for {conversation_id}")
        finally:
            store.update_conversation(conversation_id, needs_response=False)
            self.notify_done(conversation_id)
            self._running.pop(conversation_id, None)
            self._drain_queue()
            logger.info(f"Agent finished for {conversation_id}")

    async def _evict_loop(self):
        while True:
            await asyncio.sleep(30)
            now = time.monotonic()
            stale = [cid for cid, sig in self._signals.items() if sig.done and (now - sig.created_at) > 600]
            for cid in stale:
                del self._signals[cid]


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
