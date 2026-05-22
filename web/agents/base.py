"""Abstract base class for agent backends."""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, AsyncIterator

from web import config

logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    """Normalized message from agent backend (CLI or SDK)."""

    type: str  # "assistant", "tool_use", "tool_result", "system", "error"
    content: Any  # text, tool call details, etc.
    timestamp: float = field(default_factory=time.time)
    raw: dict = field(default_factory=dict)  # original message for debugging

    def to_dict(self) -> dict:
        result = {
            "type": self.type,
            "content": self.content,
            "timestamp": self.timestamp,
        }
        # Include raw data for system events (contains usage info)
        if self.type == "system" and self.raw:
            result["raw"] = self.raw
        return result


def list_md_files(directory: Path) -> list[str]:
    if not directory.exists():
        return []
    return sorted(str(p.relative_to(directory)) for p in directory.rglob("*.md"))


def build_context_index() -> str:
    sections = []

    knowledge_files = list_md_files(config.KNOWLEDGE_DIR)
    if knowledge_files:
        listing = "\n".join(f"- {config.KNOWLEDGE_DIR}/{f}" for f in knowledge_files)
        sections.append(f"## Fichiers knowledge (lire avant chaque requête)\n\n{listing}")

    cache_dir = config.DATA_DIR / "cache"
    cache_files = list_md_files(cache_dir)
    if cache_files:
        listing = "\n".join(f"- {cache_dir}/{f}" for f in cache_files)
        sections.append(f"## Fichiers cache (baselines et inventaires)\n\n{listing}")

    if not sections:
        return ""
    return "\n\n".join(sections)


def build_system_prompt() -> str | None:
    agents_md_path = config.BASE_DIR / "AGENT.md"
    if not agents_md_path.exists():
        return None
    today = date.today().strftime("%A %d %B %Y")
    agents_content = agents_md_path.read_text()
    context_index = build_context_index()
    parts = [agents_content, f"\nAujourd'hui, nous sommes le {today}."]
    if context_index:
        parts.append(f"\n# Contexte disponible\n\n{context_index}")
        parts.append(
            "\nIMPORTANT : Lis les fichiers knowledge du site concerné et les fichiers cache pertinents AVANT de lancer des requêtes."
        )
        logger.info("System prompt includes context index with knowledge and cache files")
    return "\n".join(parts)


class AgentBackend(ABC):
    """Abstract interface for Claude agent backends."""

    @abstractmethod
    async def send_message(
        self,
        conversation_id: str,
        message: str,
        history: list[dict],
        session_id: str | None = None,
        user_email: str | None = None,
    ) -> AsyncIterator[AgentMessage]:
        pass

    @abstractmethod
    async def cancel(self, conversation_id: str) -> bool:
        pass

    @abstractmethod
    def is_running(self, conversation_id: str) -> bool:
        pass
