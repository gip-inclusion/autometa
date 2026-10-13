"""Client Scalingo — lancement d'un conteneur one-off."""

import importlib

import httpx
import pytest
from sentry_sdk.scrubber import DEFAULT_DENYLIST

from web import scalingo


@pytest.fixture
def configured(mocker):
    mocker.patch.object(scalingo.config, "SCALINGO_API_TOKEN", "tk-secret")
    mocker.patch.object(scalingo.config, "SCALINGO_APP_NAME", "matometa")
    mocker.patch.object(scalingo.config, "SCALINGO_API_URL", "https://api.osc-fr1.scalingo.com")


def test_the_bearer_lives_in_a_local_sentry_knows_how_to_scrub():
    # Why: l'EventScrubber de Sentry filtre les variables locales par nom et ne connaît pas
    # `bearer` — sous ce nom, le jeton remonterait en clair dans les locals d'une exception.
    assert set(scalingo.start_one_off.__code__.co_varnames) & set(DEFAULT_DENYLIST)


def test_is_configured_requires_both_the_token_and_the_app(mocker):
    mocker.patch.object(scalingo.config, "SCALINGO_API_TOKEN", "tk-secret")
    mocker.patch.object(scalingo.config, "SCALINGO_APP_NAME", "")

    assert scalingo.is_configured() is False


def test_start_one_off_exchanges_the_token_then_returns_the_container_id(configured, mocker):
    post = mocker.patch.object(
        httpx,
        "post",
        side_effect=[
            httpx.Response(200, json={"token": "bearer-xyz"}, request=httpx.Request("POST", "https://auth")),
            httpx.Response(200, json={"container": {"id": "ctr-42"}}, request=httpx.Request("POST", "https://api")),
        ],
    )

    assert scalingo.start_one_off("python -m web.cron --app tdb1") == "ctr-42"
    assert post.call_args_list[1].kwargs["headers"]["Authorization"] == "Bearer bearer-xyz"
    assert post.call_args_list[1].kwargs["json"]["command"] == "python -m web.cron --app tdb1"
    assert all(call.kwargs["timeout"] for call in post.call_args_list)


@pytest.mark.parametrize(
    "failure",
    [
        httpx.Response(401, json={"error": "invalid"}, request=httpx.Request("POST", "https://auth")),
        httpx.ConnectError("injoignable"),
    ],
    ids=["refus", "reseau"],
)
def test_start_one_off_raises_a_scalingo_error_when_the_api_refuses_or_is_unreachable(configured, mocker, failure):
    mocker.patch.object(httpx, "post", side_effect=[failure] if isinstance(failure, Exception) else [failure])

    with pytest.raises(scalingo.ScalingoError):
        scalingo.start_one_off("python -m web.cron --app tdb1")


@pytest.mark.parametrize(
    "run_response",
    [
        httpx.Response(200, content=b"not json", request=httpx.Request("POST", "https://api")),
        httpx.Response(200, json=["oops"], request=httpx.Request("POST", "https://api")),
    ],
    ids=["corps_non_json", "corps_pas_un_dict"],
)
def test_start_one_off_raises_a_scalingo_error_when_the_run_response_is_malformed(configured, mocker, run_response):
    mocker.patch.object(
        httpx,
        "post",
        side_effect=[
            httpx.Response(200, json={"token": "bearer-xyz"}, request=httpx.Request("POST", "https://auth")),
            run_response,
        ],
    )

    with pytest.raises(scalingo.ScalingoError):
        scalingo.start_one_off("python -m web.cron --app tdb1")


@pytest.mark.parametrize(
    ("declared", "injected", "expected"),
    [
        ("", "autometa-staging", "autometa-staging"),
        ("matometa", "autometa-staging", "matometa"),
        ("", "", ""),
    ],
    ids=["injectee-par-scalingo", "surcharge-explicite", "aucune"],
)
def test_the_app_name_falls_back_to_the_one_scalingo_injects(monkeypatch, declared, injected, expected):
    # Why: `APP` est posée par la plateforme dans chaque conteneur — s'en servir évite de recopier
    # un nom d'app à la main, donc de lancer les conteneurs de staging dans la production.
    monkeypatch.setenv("SCALINGO_APP_NAME", declared)
    monkeypatch.setenv("APP", injected)
    from web import config

    try:
        importlib.reload(config)
        assert config.SCALINGO_APP_NAME == expected
    finally:
        monkeypatch.undo()
        importlib.reload(config)
