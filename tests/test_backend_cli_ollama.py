"""Tests specific to the cli-ollama backend."""

import pytest
from unittest.mock import patch


class TestCLIOllamaBackendEnv:
    def test_build_env_sets_ollama_vars(self):
        from web.agents.cli_ollama import CLIOllamaBackend
        from web import config

        backend = CLIOllamaBackend()
        env = backend._build_env("conv-123")

        assert env["ANTHROPIC_BASE_URL"] == config.OLLAMA_BASE_URL
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


class TestCLIOllamaCompat:
    def test_extract_actions_reads_json_blocks(self):
        from web.agents.cli_ollama import CLIOllamaBackend

        backend = CLIOllamaBackend()
        text = (
            "```json\n"
            "{\"name\":\"Write\",\"arguments\":{\"path\":\"index.html\",\"content\":\"x\"}}\n"
            "```"
        )

        actions = backend._extract_actions(text)
        assert actions == [{"name": "Write", "arguments": {"path": "index.html", "content": "x"}}]

    def test_infer_actions_from_marker_message(self):
        from web.agents.cli_ollama import CLIOllamaBackend

        backend = CLIOllamaBackend()
        actions = backend._infer_actions_from_message(
            "Implementez. Dans index.html, affichez exactement ce texte dans un h1: E2E-XYZ-1."
        )

        assert len(actions) == 1
        assert actions[0]["name"] == "Write"
        assert actions[0]["arguments"]["path"] == "index.html"
        assert "E2E-XYZ-1" in actions[0]["arguments"]["content"]

    def test_compat_write_and_edit(self, tmp_path):
        from web.agents.cli_ollama import CLIOllamaBackend

        backend = CLIOllamaBackend()
        workdir = str(tmp_path)

        result_write, write_mutates = backend._execute_compat_action(
            "Write",
            {"path": "index.html", "content": "<h1>ONE</h1>"},
            workdir,
        )
        assert write_mutates is True
        assert "Wrote" in result_write
        assert (tmp_path / "index.html").read_text() == "<h1>ONE</h1>"

        result_edit, edit_mutates = backend._execute_compat_action(
            "Edit",
            {"path": "index.html", "old_string": "ONE", "new_string": "TWO"},
            workdir,
        )
        assert edit_mutates is True
        assert "Edited" in result_edit
        assert (tmp_path / "index.html").read_text() == "<h1>TWO</h1>"

    def test_write_rejects_path_escape(self, tmp_path):
        from web.agents.cli_ollama import CLIOllamaBackend

        backend = CLIOllamaBackend()
        with pytest.raises(ValueError, match="outside project"):
            backend._execute_compat_action(
                "Write",
                {"path": "../escape.txt", "content": "x"},
                str(tmp_path),
            )
