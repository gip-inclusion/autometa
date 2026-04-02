"""CLI backend - spawns claude CLI process."""

import asyncio
import json
import logging
import os
import signal
from typing import AsyncIterator

import sentry_sdk

from .. import config
from .base import AgentBackend, AgentMessage, build_system_prompt

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class CLIBackend(AgentBackend):
    """Agent backend that spawns the claude CLI."""

    def __init__(self):
        self._processes: dict[str, asyncio.subprocess.Process] = {}

    def _build_env(self) -> dict:
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        return env

    def _extra_cmd_args(self) -> list[str]:
        """Extra CLI arguments appended before -p. Override in subclasses."""
        return []

    def _build_prompt(self, message: str, history: list[dict]) -> str:
        if not history:
            return message

        parts = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                parts.append(f"User: {content}")
            else:
                parts.append(f"Assistant: {content}")

        parts.append(f"User: {message}")
        return "\n\n".join(parts)

    async def send_message(
        self,
        conversation_id: str,
        message: str,
        history: list[dict],
    ) -> AsyncIterator[AgentMessage]:
        prompt = self._build_prompt(message, history)

        cmd = [
            config.CLAUDE_CLI,
            "--output-format",
            "stream-json",
            "--verbose",
        ]

        for d in config.ADDITIONAL_DIRS:
            cmd.extend(["--add-dir", d])

        system_prompt = build_system_prompt()
        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        if config.CONTAINER_ENV:
            cmd.append("--dangerously-skip-permissions")
        elif config.ALLOWED_TOOLS:
            cmd.extend(["--allowedTools", config.ALLOWED_TOOLS])

        cmd.extend(["-p", prompt])
        cmd.extend(self._extra_cmd_args())

        logger.info(f"Starting claude CLI: {' '.join(cmd[:4])}... (prompt length: {len(prompt)})")

        env = self._build_env()

        span = sentry_sdk.start_span(op="agent.cli.process", name="claude CLI subprocess")
        span.set_data("conversation_id", conversation_id)
        span.set_data("prompt_length", len(prompt))
        span.set_data("prompt_snippet", prompt[:500])

        # Spawn process (10 MB buffer to handle large tool results)
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(config.BASE_DIR),
            env=env,
            limit=10 * 1024 * 1024,
        )

        logger.info(f"Process started with PID: {process.pid}")

        self._processes[conversation_id] = process

        stderr_task = asyncio.create_task(self._drain_stderr(process.stderr))

        last_events: list[str] = []

        try:
            # Read stdout line by line (stderr drained in parallel to avoid pipe deadlock)
            line_count = 0
            while True:
                line = await process.stdout.readline()
                if not line:
                    logger.debug(f"EOF reached after {line_count} lines")
                    break

                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue

                line_count += 1
                logger.debug("Line %d: %s", line_count, line_str)

                try:
                    event = json.loads(line_str)
                    for agent_msg in self._parse_events(event):
                        logger.debug(f"Parsed event: {agent_msg.type}")
                        last_events.append(f"{agent_msg.type}: {str(agent_msg.content)[:200]}")
                        if len(last_events) > 10:
                            last_events.pop(0)
                        yield agent_msg
                except json.JSONDecodeError:
                    logger.warning("Non-JSON line: %s", line_str)
                    yield AgentMessage(
                        type="system",
                        content=line_str,
                        raw={"raw_line": line_str},
                    )

            await process.wait()
            span.set_data("line_count", line_count)
            logger.info(f"Process exited with code: {process.returncode}")
        finally:
            self._processes.pop(conversation_id, None)
            if process.returncode is None:
                try:
                    process.send_signal(signal.SIGTERM)
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError, ProcessLookupError:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        logger.debug("Process already exited before kill")
            stderr_bytes = await stderr_task
            logger.info(f"Cleaned up conversation {conversation_id}")

        stderr_str = stderr_bytes.decode("utf-8", errors="replace")
        span.set_data("exit_code", process.returncode)

        if process.returncode != 0:
            stderr_tail = stderr_str[-2000:] if len(stderr_str) > 2000 else stderr_str
            span.set_status("internal_error")
            span.set_data("stderr", stderr_tail)
            span.set_data("last_events", last_events)

            with sentry_sdk.push_scope() as scope:
                scope.set_extra("conversation_id", conversation_id)
                scope.set_extra("exit_code", process.returncode)
                scope.set_extra("stderr", stderr_tail)
                scope.set_extra("prompt_snippet", prompt[:500])
                scope.set_extra("last_events", last_events)
                sentry_sdk.capture_message(
                    f"CLI process error (exit {process.returncode})",
                    level="error",
                    scope=scope,
                )
            logger.error(
                "CLI process error: conversation=%s exit_code=%s stderr=%s",
                conversation_id,
                process.returncode,
                stderr_tail,
            )

            yield AgentMessage(
                type="error",
                content=f"Process exited with code {process.returncode}: {stderr_str}",
                raw={"stderr": stderr_str, "code": process.returncode},
            )
        span.finish()

    @staticmethod
    async def _drain_stderr(stream: asyncio.StreamReader) -> bytes:
        chunks: list[bytes] = []
        while True:
            line = await stream.readline()
            if not line:
                break
            chunks.append(line)
        return b"".join(chunks)

    def _parse_events(self, event: dict) -> list[AgentMessage]:
        event_type = event.get("type")

        if event_type == "assistant":
            msg_payload = event.get("message", {})
            content_blocks = msg_payload.get("content", [])

            messages: list[AgentMessage] = []
            for block in content_blocks:
                block_type = block.get("type")

                if block_type == "text":
                    text = block.get("text", "").strip()
                    if text:
                        messages.append(
                            AgentMessage(
                                type="assistant",
                                content=text,
                                raw=event,
                            )
                        )

                elif block_type == "tool_use":
                    messages.append(
                        AgentMessage(
                            type="tool_use",
                            content={
                                "tool": block.get("name"),
                                "input": block.get("input"),
                            },
                            raw=event,
                        )
                    )

            return messages

        if event_type == "tool_use":
            return [
                AgentMessage(
                    type="tool_use",
                    content={
                        "tool": event.get("tool") or event.get("name"),
                        "input": event.get("input"),
                    },
                    raw=event,
                )
            ]

        if event_type == "tool_result":
            return [
                AgentMessage(
                    type="tool_result",
                    content={
                        "tool": event.get("tool"),
                        "output": event.get("output"),
                    },
                    raw=event,
                )
            ]

        if event_type == "user":
            msg_payload = event.get("message", {})
            content_blocks = msg_payload.get("content", [])

            for block in content_blocks:
                if block.get("type") == "tool_result":
                    result_content = block.get("content", "")
                    return [
                        AgentMessage(
                            type="tool_result",
                            content={
                                "tool": block.get("tool_use_id", "")[:8],
                                "output": result_content,
                            },
                            raw=event,
                        )
                    ]
            return []

        if event_type == "system":
            return [
                AgentMessage(
                    type="system",
                    content=event.get("message") or event.get("subtype"),
                    raw=event,
                )
            ]

        if event_type == "error":
            return [
                AgentMessage(
                    type="error",
                    content=event.get("message") or str(event),
                    raw=event,
                )
            ]

        if event_type == "result":
            raw = dict(event)
            if "usage" in event:
                raw["usage"] = event["usage"]
            return [
                AgentMessage(
                    type="system",
                    content=f"Completed: {event.get('subtype', 'done')}",
                    raw=raw,
                )
            ]

        return []

    async def cancel(self, conversation_id: str) -> bool:
        process = self._processes.get(conversation_id)
        if not process:
            return False

        try:
            process.send_signal(signal.SIGTERM)
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            process.kill()

        self._processes.pop(conversation_id, None)
        return True

    @property
    def _running(self) -> set[str]:
        return {conv_id for conv_id, process in self._processes.items() if process.returncode is None}

    def is_running(self, conversation_id: str) -> bool:
        process = self._processes.get(conversation_id)
        return process is not None and process.returncode is None
