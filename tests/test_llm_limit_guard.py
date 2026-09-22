"""Les prompts courts (titre, tags) ne martèlent pas un moteur déjà épuisé."""

import httpx
import pytest

from web import llm
from web.llm_errors import LLMError


def test_a_limited_backend_without_fallback_short_circuits_before_the_cli_retries(mocker):
    """Sans ce garde-fou, chaque nouvelle conversation d'une fenêtre de limite brûle la série
    complète de retries du CLI (~174 s) pour un titre qui sera vide de toute façon."""
    mocker.patch.object(llm, "backend_is_limited", return_value=True)
    mocker.patch.object(llm.config, "AGENT_FALLBACK_BACKEND", "")
    call = mocker.patch.object(llm, "llm_call")

    with pytest.raises(LLMError):
        llm.generate_text("résume ceci")

    call.assert_not_called()


def test_a_limited_backend_hands_short_prompts_to_the_fallback(mocker):
    """B7 : avec un secours, titres et tags suivent la conversation au lieu d'échouer — avec le modèle
    du secours, pas celui du moteur limité."""
    mocker.patch.object(llm, "backend_is_limited", return_value=True)
    mocker.patch.object(llm.config, "AGENT_FALLBACK_BACKEND", "cli-ollama")
    ollama = mocker.patch.object(llm, "ollama_generate", return_value="Un titre")

    assert llm.generate_text("résume ceci", model="claude-haiku-4-5") == "Un titre"
    assert ollama.call_args.kwargs["model"] == llm.config.OLLAMA_MODEL


def test_an_available_backend_is_called_normally(mocker):
    mocker.patch.object(llm, "backend_is_limited", return_value=False)
    mocker.patch.object(llm, "llm_call", return_value="Un titre")

    assert llm.generate_text("résume ceci") == "Un titre"


@pytest.mark.parametrize("api_key, expected", [("sk-abc", {"Authorization": "Bearer sk-abc"}), ("", {})])
def test_ollama_generate_sends_the_cloud_key(mocker, api_key, expected):
    """B6 : l'URL bascule sur Ollama Cloud avec la clé, la requête doit donc la porter."""
    mocker.patch.object(llm.config, "OLLAMA_API_KEY", api_key)
    post = mocker.patch.object(
        llm.httpx,
        "post",
        return_value=httpx.Response(200, json={"response": "ok"}, request=httpx.Request("POST", "http://x")),
    )

    llm.ollama_generate("p", model="m", max_tokens=10, temperature=0.1, timeout=5)

    assert post.call_args.kwargs["headers"] == expected
