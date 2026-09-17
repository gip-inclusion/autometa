"""CLI-Ollama backend — Claude Code CLI pointed at Ollama's Anthropic-compatible API."""

from web import config

from .cli import CLIBackend


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
        return env

    def _extra_cmd_args(self) -> list[str]:
        return ["--model", config.OLLAMA_MODEL]
