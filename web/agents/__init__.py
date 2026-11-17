"""Agent backend implementations."""

from web import config

from .base import AgentBackend, AgentMessage
from .cli import CLIBackend
from .cli_ollama import CLIOllamaBackend
from .fake import FakeBackend

__all__ = [
    "AgentBackend",
    "AgentMessage",
    "get_agent",
]

_BACKENDS = {"cli": CLIBackend, "cli-ollama": CLIOllamaBackend, "fake": FakeBackend}
_instances: dict[str, AgentBackend] = {}


def get_agent(backend: str | None = None) -> AgentBackend:
    name = backend or config.AGENT_BACKEND
    if name not in _BACKENDS:
        raise ValueError(f"Unknown AGENT_BACKEND: {name}")
    if name == "fake" and config.ENV.is_server:
        raise ValueError("AGENT_BACKEND=fake n'est permis qu'en local")
    # Why: le backend porte la table des sous-processus en cours ; une instance neuve par tour
    # perdrait la trace des processus à annuler.
    if name not in _instances:
        _instances[name] = _BACKENDS[name]()
    return _instances[name]
