"""Tests specific to the cli-ollama backend."""

from datetime import datetime, timezone

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


def test_build_env_maps_the_cli_small_model_to_ollama(mocker):
    """Les sous-agents du CLI demandent un modèle Haiku qu'Ollama ne sert pas."""
    mock_config = mocker.patch("web.agents.cli_ollama.config")
    mock_config.OLLAMA_SMALL_MODEL = "gemma-small"

    assert CLIOllamaBackend()._build_env()["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "gemma-small"


@pytest.mark.parametrize(
    "text, limited",
    [
        ('API Error: 429 {"error": "you have reached your session usage limit, upgrade for higher limits"}', True),
        (
            'API Error: 429 {"error": "you\'ve reached your hourly usage limit, please wait or upgrade to continue"}',
            True,
        ),
        ('API Error: 429 {"error": "too many concurrent requests"}', False),
        ("hit your limit · resets 5pm (UTC)", False),
    ],
)
def test_an_exhausted_ollama_quota_is_a_limit_with_an_hour_window(text, limited):
    reset = CLIOllamaBackend()._usage_limit_reset(text)

    assert (reset is not None) is limited
    if limited:
        assert 3500 < (reset - datetime.now(timezone.utc)).total_seconds() <= 3600
