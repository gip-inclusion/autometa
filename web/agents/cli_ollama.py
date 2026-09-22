"""CLI-Ollama backend — Claude Code CLI pointed at Ollama's Anthropic-compatible API."""

import re
from datetime import datetime, timedelta, timezone

from web import config

from .cli import CLIBackend

# Ollama Cloud refuse un quota épuisé par un 429 « you have reached your session usage limit » ou
# « you've reached your hourly usage limit », que le CLI rend en « API Error: 429 … ».
_OLLAMA_LIMIT_RE = re.compile(r"API Error:\s*429\b.*\busage limit\b", re.I | re.S)


class CLIOllamaBackend(CLIBackend):
    """CLIBackend that routes through Ollama instead of Anthropic."""

    @property
    def model_label(self) -> str:
        return config.OLLAMA_MODEL

    def _build_env(self, *, conversation_id: str | None = None, user_email: str | None = None) -> dict:
        env = super()._build_env(conversation_id=conversation_id, user_email=user_email)
        env["ANTHROPIC_BASE_URL"] = config.OLLAMA_BASE_URL
        # Why: une instance Ollama locale ignore le jeton ; Ollama Cloud le rejette s'il est vide.
        env["ANTHROPIC_AUTH_TOKEN"] = config.OLLAMA_API_KEY or "ollama"
        env["ANTHROPIC_API_KEY"] = ""
        # Why: sans lui, les sous-agents et tâches de fond du CLI demandent un modèle Haiku qu'Ollama ne sert pas.
        env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = config.OLLAMA_SMALL_MODEL
        return env

    def _extra_cmd_args(self) -> list[str]:
        return ["--model", config.OLLAMA_MODEL]

    def _usage_limit_reset(self, text: str) -> datetime | None:
        if not _OLLAMA_LIMIT_RE.search(text):
            return None
        # Why: Ollama n'annonce pas l'heure de reprise ; sa fenêtre la plus courte est horaire.
        return datetime.now(timezone.utc) + timedelta(hours=1)
