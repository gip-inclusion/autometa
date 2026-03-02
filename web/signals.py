"""In-process signal registry for PM → SSE communication.

Replaces DB polling with asyncio.Event signaling. Works because PM and SSE
share the same asyncio event loop (FastAPI lifespan in web/app.py).
"""

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class ConversationSignal:
    message_event: asyncio.Event = field(default_factory=asyncio.Event)
    finished: bool = False


class SignalRegistry:
    def __init__(self):
        self._signals: dict[str, ConversationSignal] = {}
        self._pm_alive_at: float = 0.0

    def _get_or_create(self, conv_id: str) -> ConversationSignal:
        if conv_id not in self._signals:
            self._signals[conv_id] = ConversationSignal()
        return self._signals[conv_id]

    # -- Called by PM --

    def notify_message(self, conv_id: str) -> None:
        """Signal that a new message was written for this conversation."""
        sig = self._get_or_create(conv_id)
        sig.message_event.set()

    def notify_finished(self, conv_id: str) -> None:
        """Signal that the PM finished processing this conversation."""
        sig = self._get_or_create(conv_id)
        sig.finished = True
        sig.message_event.set()  # wake SSE so it sees finished=True

    def update_pm_alive(self) -> None:
        """Record that the PM is alive (called alongside DB heartbeat)."""
        self._pm_alive_at = time.monotonic()

    # -- Called by SSE --

    async def wait_for_message(self, conv_id: str, timeout: float = 3.0) -> bool:
        """Wait for a message signal. Returns True if signaled, False on timeout."""
        sig = self._get_or_create(conv_id)
        try:
            await asyncio.wait_for(sig.message_event.wait(), timeout=timeout)
            sig.message_event.clear()
            return True
        except asyncio.TimeoutError:
            return False

    def is_finished(self, conv_id: str) -> bool:
        """Check if the PM has finished processing this conversation."""
        sig = self._signals.get(conv_id)
        return sig is not None and sig.finished

    def is_pm_alive(self, max_age: float = 30.0) -> bool:
        """Check if the PM has signaled liveness recently."""
        if self._pm_alive_at == 0.0:
            return False
        return (time.monotonic() - self._pm_alive_at) < max_age

    def cleanup(self, conv_id: str) -> None:
        """Remove signal state for a conversation (call on stream end)."""
        self._signals.pop(conv_id, None)


signals = SignalRegistry()
