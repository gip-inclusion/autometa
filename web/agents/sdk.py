"""SDK backend stub - uses Claude Agent SDK (not yet implemented)."""

from typing import AsyncIterator, Optional

from .base import AgentBackend, AgentMessage


class SDKBackend(AgentBackend):
    """
    Agent backend using the Claude Agent SDK.

    This is a stub for future implementation. The SDK provides:
    - Finer-grained streaming (content_block_delta events)
    - Native session management
    - Better suited for remote deployment

    See: https://docs.anthropic.com/en/docs/claude-agent-sdk
    """

    def __init__(self):
        raise NotImplementedError(
            "SDK backend not yet implemented. "
            "Set AGENT_BACKEND=cli to use the CLI backend."
        )

    async def send_message(
        self,
        conversation_id: str,
        message: str,
        history: list[dict],
        session_id: Optional[str] = None,
    ) -> AsyncIterator[AgentMessage]:
        """Send message via SDK - not implemented."""
        raise NotImplementedError

    async def cancel(self, conversation_id: str) -> bool:
        """Cancel via SDK - not implemented."""
        raise NotImplementedError

    def is_running(self, conversation_id: str) -> bool:
        """Check running state via SDK - not implemented."""
        raise NotImplementedError
