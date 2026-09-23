"""Generic backend tests — dispatch and LLM routing for all backends."""

import pytest


@pytest.mark.parametrize(
    "name,cls_name",
    [
        ("cli", "CLIBackend"),
        ("cli-ollama", "CLIOllamaBackend"),
    ],
)
def test_get_agent_returns_correct_class(mocker, name, cls_name):
    from web.agents import get_agent

    mocker.patch("web.config.AGENT_BACKEND", name)
    agent = get_agent()
    assert type(agent).__name__ == cls_name


def test_get_agent_unknown_raises(mocker):
    from web.agents import get_agent

    mocker.patch("web.config.AGENT_BACKEND", "nope")
    with pytest.raises(ValueError, match="Unknown"):
        get_agent()


def test_get_agent_accepts_explicit_backend():
    from web.agents import get_agent
    from web.agents.cli_ollama import CLIOllamaBackend

    assert isinstance(get_agent("cli-ollama"), CLIOllamaBackend)


def test_get_agent_reuses_instance_per_backend():
    from web.agents import get_agent

    assert get_agent("cli") is get_agent("cli")
    assert get_agent("cli") is not get_agent("cli-ollama")


@pytest.mark.parametrize(
    "backend,target",
    [
        ("cli-ollama", "web.llm.ollama_generate"),
        ("ollama", "web.llm.ollama_generate"),
        ("cli", "web.llm.llm_call"),
    ],
)
def test_llm_routes_to_correct_generator(mocker, backend, target):
    mocker.patch("web.llm.get_llm_backend", return_value=backend)
    mock_gen = mocker.patch(target, return_value="ok")
    from web.llm import generate_text

    result = generate_text("test")

    mock_gen.assert_called_once()
    assert result == "ok"
