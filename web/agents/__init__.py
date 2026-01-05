"""Agent backend implementations."""

from .base import AgentBackend, AgentMessage
from .cli import CLIBackend

__all__ = ["AgentBackend", "AgentMessage", "CLIBackend", "get_agent"]


def get_agent() -> AgentBackend:
    """Get the configured agent backend."""
    from .. import config

    if config.AGENT_BACKEND == "sdk":
        from .sdk import SDKBackend
        return SDKBackend()
    else:
        return CLIBackend()
