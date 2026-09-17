"""Agent backend implementations."""

from web import config

from .base import AgentBackend, AgentMessage
from .cli import CLIBackend
from .cli_ollama import CLIOllamaBackend

__all__ = [
    "AgentBackend",
    "AgentMessage",
    "get_agent",
]

_BACKENDS = {"cli": CLIBackend, "cli-ollama": CLIOllamaBackend}
_instances: dict[str, AgentBackend] = {}


def get_agent(backend: str | None = None) -> AgentBackend:
    name = backend or config.AGENT_BACKEND
    if name not in _BACKENDS:
        raise ValueError(f"Unknown AGENT_BACKEND: {name}")
    # Why: le backend porte la table des sous-processus en cours ; une instance neuve par tour
    # perdrait la trace des processus à annuler.
    if name not in _instances:
        _instances[name] = _BACKENDS[name]()
    return _instances[name]
