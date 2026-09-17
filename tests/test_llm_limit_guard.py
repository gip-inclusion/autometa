"""Les prompts courts (titre, tags) ne martèlent pas un moteur déjà épuisé."""

import pytest

from web import llm
from web.llm_errors import LLMError


def _redis(mocker, exists):
    client = mocker.MagicMock()
    client.exists.return_value = 1 if exists else 0
    client.__enter__.return_value = client
    mocker.patch.object(llm.redis.Redis, "from_url", return_value=client)
    return client


def test_a_limited_backend_short_circuits_before_the_cli_retries(mocker):
    """Sans ce garde-fou, chaque nouvelle conversation d'une fenêtre de limite brûle la série
    complète de retries du CLI (~174 s) pour un titre qui sera vide de toute façon."""
    _redis(mocker, exists=True)
    call = mocker.patch.object(llm, "llm_call")

    with pytest.raises(LLMError):
        llm.generate_text("résume ceci")

    call.assert_not_called()


def test_an_available_backend_is_called_normally(mocker):
    _redis(mocker, exists=False)
    mocker.patch.object(llm, "llm_call", return_value="Un titre")

    assert llm.generate_text("résume ceci") == "Un titre"


def test_the_limit_key_is_the_one_the_runner_writes(mocker):
    """Une clé divergente rendrait le garde-fou muet sans que rien ne le signale."""
    client = _redis(mocker, exists=False)
    mocker.patch.object(llm, "llm_call", return_value="x")

    llm.generate_text("p")

    client.exists.assert_called_once_with("autometa:limit:cli")


def test_a_redis_outage_does_not_block_short_prompts(mocker):
    """Panne Redis : on préfère un titre qui échoue en aval à un titre jamais tenté."""
    mocker.patch.object(llm.redis.Redis, "from_url", side_effect=llm.redis.RedisError("down"))
    mocker.patch.object(llm, "llm_call", return_value="Un titre")

    assert llm.generate_text("p") == "Un titre"
