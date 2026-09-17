"""Tests specific to the cli-ollama backend."""

import pytest

from web.agents.cli_ollama import CLIOllamaBackend


@pytest.mark.parametrize(
    "api_key, expected_token",
    [("sk-abc", "sk-abc"), ("", "ollama")],
)
def test_build_env_uses_configured_api_key(mocker, api_key, expected_token):
    mock_config = mocker.patch("web.agents.cli_ollama.config")
    mock_config.OLLAMA_BASE_URL = "https://ollama.com"
    mock_config.OLLAMA_API_KEY = api_key
    env = CLIOllamaBackend()._build_env()

    assert env["ANTHROPIC_BASE_URL"] == "https://ollama.com"
    assert env["ANTHROPIC_AUTH_TOKEN"] == expected_token
    assert env["ANTHROPIC_API_KEY"] == ""


def test_build_env_respects_custom_ollama_url(mocker):
    from web.agents.cli_ollama import CLIOllamaBackend

    mock_config = mocker.patch("web.agents.cli_ollama.config")
    mock_config.OLLAMA_BASE_URL = "http://gpu-server:11434"
    mock_config.OLLAMA_MODEL = "qwen3-coder"
    backend = CLIOllamaBackend()
    env = backend._build_env()

    assert env["ANTHROPIC_BASE_URL"] == "http://gpu-server:11434"


def test_extra_cmd_args_includes_model(mocker):
    from web.agents.cli_ollama import CLIOllamaBackend

    mock_config = mocker.patch("web.agents.cli_ollama.config")
    mock_config.OLLAMA_MODEL = "glm-4.7"
    backend = CLIOllamaBackend()
    args = backend._extra_cmd_args()

    assert args == ["--model", "glm-4.7"]
