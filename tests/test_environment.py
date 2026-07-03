import importlib

import pytest

from web.environment import Environment


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, Environment.DEV),
        ("", Environment.DEV),
        ("dev", Environment.DEV),
        ("review", Environment.REVIEW),
        ("staging", Environment.STAGING),
        ("prod", Environment.PROD),
    ],
)
def test_current_resolves_known_values(raw, expected):
    assert Environment.current(raw) is expected


@pytest.mark.parametrize("raw", ["live", "prd", "Production", "staign"])
def test_current_fails_loud_on_unknown_value(raw):
    with pytest.raises(ValueError):
        Environment.current(raw)


@pytest.mark.parametrize(
    ("env", "is_server"),
    [
        (Environment.DEV, False),
        (Environment.REVIEW, True),
        (Environment.STAGING, True),
        (Environment.PROD, True),
    ],
)
def test_is_server_is_true_off_local(env, is_server):
    assert env.is_server is is_server


@pytest.mark.parametrize(
    ("env", "owns"),
    [
        (Environment.DEV, False),
        (Environment.REVIEW, False),
        (Environment.STAGING, False),
        (Environment.PROD, True),
    ],
)
def test_only_prod_owns_the_shared_db(env, owns):
    assert env.owns_shared_db is owns


def test_config_reports_invalid_env_to_sentry(monkeypatch, mocker):
    monkeypatch.setenv("AUTOMETA_ENV", "live")
    init = mocker.patch("sentry_sdk.init")
    capture = mocker.patch("sentry_sdk.capture_exception")
    mocker.patch("sentry_sdk.flush")
    from web import config

    try:
        with pytest.raises(ValueError):
            importlib.reload(config)
        init.assert_called_once()
        capture.assert_called_once()
    finally:
        monkeypatch.delenv("AUTOMETA_ENV", raising=False)
        importlib.reload(config)
