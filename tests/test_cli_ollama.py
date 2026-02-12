"""Tests for the cli-ollama backend."""

from unittest.mock import patch

import pytest


class TestCLIOllamaBackendEnv:
    def test_build_env_sets_ollama_vars(self):
        from web.agents.cli_ollama import CLIOllamaBackend

        backend = CLIOllamaBackend()
        env = backend._build_env("conv-123")

        assert env["ANTHROPIC_BASE_URL"] == "http://localhost:11434"
        assert env["ANTHROPIC_AUTH_TOKEN"] == "ollama"
        assert env["ANTHROPIC_API_KEY"] == ""
        assert env["MATOMETA_CONVERSATION_ID"] == "conv-123"

    def test_build_env_respects_custom_ollama_url(self):
        from web.agents.cli_ollama import CLIOllamaBackend

        with patch("web.agents.cli_ollama.config") as mock_config:
            mock_config.OLLAMA_BASE_URL = "http://gpu-server:11434"
            mock_config.OLLAMA_MODEL = "qwen3-coder"
            backend = CLIOllamaBackend()
            env = backend._build_env("conv-456")

        assert env["ANTHROPIC_BASE_URL"] == "http://gpu-server:11434"

    def test_extra_cmd_args_includes_model(self):
        from web.agents.cli_ollama import CLIOllamaBackend

        with patch("web.agents.cli_ollama.config") as mock_config:
            mock_config.OLLAMA_MODEL = "glm-4.7"
            backend = CLIOllamaBackend()
            args = backend._extra_cmd_args()

        assert args == ["--model", "glm-4.7"]


class TestCLIBackendHooks:
    """Verify the base CLIBackend hooks have the expected defaults."""

    def test_build_env_removes_api_key(self):
        from web.agents.cli import CLIBackend

        backend = CLIBackend()
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-secret", "HOME": "/x"}, clear=True):
            env = backend._build_env("conv-1")

        assert "ANTHROPIC_API_KEY" not in env
        assert env["HOME"] == "/x"
        assert env["MATOMETA_CONVERSATION_ID"] == "conv-1"

    def test_extra_cmd_args_empty(self):
        from web.agents.cli import CLIBackend

        backend = CLIBackend()
        assert backend._extra_cmd_args() == []


class TestGetAgent:
    """Every registered backend must return the right class."""

    @pytest.mark.parametrize("name,cls_name", [
        ("ollama", "OllamaBackend"),
        ("cli", "CLIBackend"),
        ("cli-ollama", "CLIOllamaBackend"),
        ("sdk", "SDKBackend"),
    ])
    def test_get_agent_returns_correct_class(self, name, cls_name):
        from web.agents import get_agent

        with patch("web.config.AGENT_BACKEND", name):
            agent = get_agent()

        assert type(agent).__name__ == cls_name

    def test_get_agent_unknown_raises(self):
        from web.agents import get_agent

        with patch("web.config.AGENT_BACKEND", "nope"):
            with pytest.raises(ValueError, match="Unknown"):
                get_agent()


class TestLLMRouting:
    """LLM short-prompt routing for every backend."""

    @pytest.mark.parametrize("backend,expected_fn", [
        ("ollama", "_ollama_generate"),
        ("cli-ollama", "_ollama_generate"),
        ("cli", "_claude_cli_generate"),
        ("sdk", "_anthropic_generate"),
    ])
    def test_routes_to_correct_generator(self, backend, expected_fn):
        with patch("web.llm._get_llm_backend", return_value=backend), \
             patch(f"web.llm.{expected_fn}", return_value="ok") as mock_gen:
            from web.llm import generate_text
            result = generate_text("test")

        mock_gen.assert_called_once()
        assert result == "ok"
