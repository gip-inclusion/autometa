"""SDK backend — uses claude_agent_sdk.query() instead of raw subprocess."""

import asyncio
import logging
from typing import AsyncIterator

import sentry_sdk
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    query,
)
from claude_agent_sdk._errors import ProcessError

from .. import config
from .base import AgentBackend, AgentMessage, build_system_prompt

logger = logging.getLogger(__name__)


class SDKBackend(AgentBackend):
    """Agent backend using the Claude Agent SDK (query + resume)."""

    def __init__(self):
        self._cancel_events: dict[str, asyncio.Event] = {}

    # ------------------------------------------------------------------
    # Prompt construction (same as CLIBackend)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(message: str, history: list[dict]) -> str:
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

    # ------------------------------------------------------------------
    # SDK options construction
    # ------------------------------------------------------------------

    def _build_options(self, conversation_id: str) -> ClaudeAgentOptions:
        system_prompt = build_system_prompt()

        if config.CONTAINER_ENV:
            permission_mode = "bypassPermissions"
            allowed_tools = []
        elif config.ALLOWED_TOOLS:
            permission_mode = "default"
            allowed_tools = [t.strip() for t in config.ALLOWED_TOOLS.split(",") if t.strip()]
        else:
            permission_mode = "default"
            allowed_tools = []

        return ClaudeAgentOptions(
            system_prompt=system_prompt,
            permission_mode=permission_mode,
            allowed_tools=allowed_tools,
            cwd=str(config.BASE_DIR),
            cli_path=config.CLAUDE_CLI,
            add_dirs=list(config.ADDITIONAL_DIRS),
            env={"ANTHROPIC_API_KEY": ""},
            max_buffer_size=10 * 1024 * 1024,
        )

    # ------------------------------------------------------------------
    # Main interface
    # ------------------------------------------------------------------

    async def send_message(
        self,
        conversation_id: str,
        message: str,
        history: list[dict],
    ) -> AsyncIterator[AgentMessage]:
        prompt = self._build_prompt(message, history)
        options = self._build_options(conversation_id)
        cancel_event = asyncio.Event()
        self._cancel_events[conversation_id] = cancel_event

        logger.info(f"Starting SDK query (prompt length: {len(prompt)})")

        with sentry_sdk.start_span(op="agent.sdk.query", name="claude-agent-sdk query") as span:
            span.set_data("prompt_length", len(prompt))
            try:
                async for sdk_msg in query(prompt=prompt, options=options):
                    if cancel_event.is_set():
                        break
                    for agent_msg in self._translate_message(sdk_msg):
                        yield agent_msg
            except ProcessError as e:
                logger.error(f"SDK ProcessError: {e} (exit_code={e.exit_code})")
                span.set_status("internal_error")
                yield AgentMessage(
                    type="error",
                    content=f"Process exited with code {e.exit_code}: {e.stderr or e}",
                    raw={"stderr": e.stderr, "code": e.exit_code},
                )
            # Why: catch-all needed because the SDK may raise arbitrary errors during streaming
            # and we must always yield an error message rather than crash the async generator.
            except Exception as e:
                logger.exception(f"SDK error for {conversation_id}")
                span.set_status("internal_error")
                sentry_sdk.capture_exception()
                yield AgentMessage(type="error", content=str(e), raw={})
            finally:
                self._cancel_events.pop(conversation_id, None)
                logger.info(f"SDK query finished for {conversation_id}")

    # ------------------------------------------------------------------
    # Message translation
    # ------------------------------------------------------------------

    @staticmethod
    def _translate_message(sdk_msg) -> list[AgentMessage]:
        msgs: list[AgentMessage] = []

        if isinstance(sdk_msg, AssistantMessage):
            for block in sdk_msg.content:
                if isinstance(block, TextBlock):
                    text = block.text.strip()
                    if text:
                        msgs.append(AgentMessage(type="assistant", content=text, raw={}))
                elif isinstance(block, ToolUseBlock):
                    msgs.append(
                        AgentMessage(
                            type="tool_use",
                            content={"tool": block.name, "input": block.input},
                            raw={},
                        )
                    )

        elif isinstance(sdk_msg, SystemMessage):
            raw = {"subtype": sdk_msg.subtype, **sdk_msg.data}
            msgs.append(AgentMessage(type="system", content=sdk_msg.subtype, raw=raw))

        elif isinstance(sdk_msg, ResultMessage):
            raw = {"subtype": sdk_msg.subtype, "type": "result"}
            if sdk_msg.usage:
                raw["usage"] = sdk_msg.usage
            if sdk_msg.total_cost_usd is not None:
                raw["total_cost_usd"] = sdk_msg.total_cost_usd
            msgs.append(
                AgentMessage(
                    type="system",
                    content=f"Completed: {sdk_msg.subtype}",
                    raw=raw,
                )
            )

        # UserMessage (tool results) — pass through for PM to see tool_result events
        else:
            # Check if it's a UserMessage with tool results
            content = getattr(sdk_msg, "content", None)
            if isinstance(content, list):
                for block in content:
                    tool_use_id = getattr(block, "tool_use_id", None)
                    if tool_use_id:
                        block_content = getattr(block, "content", "")
                        msgs.append(
                            AgentMessage(
                                type="tool_result",
                                content={"tool": tool_use_id[:8], "output": block_content},
                                raw={},
                            )
                        )

        return msgs

    # ------------------------------------------------------------------
    # Cancellation & status
    # ------------------------------------------------------------------

    async def cancel(self, conversation_id: str) -> bool:
        event = self._cancel_events.get(conversation_id)
        if event:
            event.set()
            return True
        return False

    def is_running(self, conversation_id: str) -> bool:
        return conversation_id in self._cancel_events
