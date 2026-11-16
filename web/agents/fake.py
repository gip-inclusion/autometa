"""Moteur factice des parcours de navigateur : chaque tour est scénarisé par des marqueurs dans le message."""

import asyncio
import re
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

from .base import AgentBackend, AgentMessage


async def stopped(stop: asyncio.Event, timeout: float) -> bool:
    """Attend au plus `timeout` secondes qu'on arrête le tour ; vrai s'il a été arrêté."""
    try:
        await asyncio.wait_for(stop.wait(), timeout)
    except TimeoutError:
        return False
    return True


class FakeBackend(AgentBackend):
    """Répond sans modèle selon [tools:N], [slow:N], [hang], [error], [limit] ; sinon une réponse factice."""

    def __init__(self):
        self._stops: dict[str, asyncio.Event] = {}

    async def send_message(
        self,
        conversation_id: str,
        message: str,
        history: list[dict],
        session_id: str | None = None,
        user_email: str | None = None,
    ) -> AsyncIterator[AgentMessage]:
        stop = self._stops[conversation_id] = asyncio.Event()
        markers = {
            name: int(count or 1)
            for name, count in re.findall(r"\[(slow|tools|error|limit|hang)(?::(\d+))?\]", message)
        }
        try:
            for i in range(markers.get("tools", 0)):
                yield AgentMessage(type="tool_use", content={"tool": "Bash", "input": {"command": f"echo {i}"}})
                yield AgentMessage(type="tool_result", content={"tool": "Bash", "output": str(i)})
            for i in range(markers.get("slow", 0)):
                if await stopped(stop, 1):
                    return
                yield AgentMessage(type="assistant", content=f"Morceau {i + 1}.")
            if "hang" in markers:
                await stop.wait()
                return
            if "error" in markers:
                yield AgentMessage(type="error", content="Erreur factice.")
            elif "limit" in markers:
                # Why: la limite marque le moteur bloqué jusqu'à sa reprise ; courte, elle ne gêne pas les tours suivants.
                reset = datetime.now(timezone.utc) + timedelta(seconds=5)
                yield AgentMessage(type="limit", content="Limite d'usage factice.", raw={"reset": reset.isoformat()})
            else:
                yield AgentMessage(type="assistant", content=f"Réponse factice : {message}")
        finally:
            if self._stops.get(conversation_id) is stop:
                del self._stops[conversation_id]

    async def cancel(self, conversation_id: str) -> bool:
        stop = self._stops.get(conversation_id)
        if stop is None:
            return False
        stop.set()
        return True

    def is_running(self, conversation_id: str) -> bool:
        return conversation_id in self._stops
