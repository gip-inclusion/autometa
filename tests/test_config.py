"""Config env-var wiring tests."""

import importlib

import pytest

from web import config


@pytest.mark.parametrize(
    ("app", "expected"),
    [("autometa-staging-pr214", "autometa-staging-pr214"), (None, "staging")],
    ids=["scalingo", "fallback"],
)
def test_app_name_reads_scalingo_app_or_falls_back_to_the_environment(monkeypatch, app, expected):
    """Un mauvais nom de variable afficherait `[staging]` au lieu de l'app : exactement ce que le préfixe Slack corrige."""
    monkeypatch.setenv("AUTOMETA_ENV", "staging")
    if app is None:
        monkeypatch.delenv("APP", raising=False)
    else:
        monkeypatch.setenv("APP", app)
    import web.config as c

    importlib.reload(c)
    assert c.APP_NAME == expected
    importlib.reload(c)


def test_rpe_signature_env_vars(monkeypatch):
    monkeypatch.setenv("RPE_PERMUTATION", "PERM")
    monkeypatch.setenv("RPE_STRONG_NAME", "STRONG")
    monkeypatch.setenv("RPE_POLICY_LOGIN", "PLOG")
    monkeypatch.setenv("RPE_POLICY_DASH", "PDASH")
    import web.config as c

    importlib.reload(c)
    assert (c.RPE_PERMUTATION, c.RPE_STRONG_NAME, c.RPE_POLICY_LOGIN, c.RPE_POLICY_DASH) == (
        "PERM",
        "STRONG",
        "PLOG",
        "PDASH",
    )
    importlib.reload(c)


def test_public_dashboards_buckets_read_deployment_env_var_names():
    # Why: the public buckets are provisioned under PUBLIC_DASHBOARDS_BUCKET_<ENV>
    # (conftest sets those names); a divergent key silently resolves to None and
    # blocks publication with public-bucket-not-configured.
    assert config.PUBLIC_S3_BUCKET_STAGING == "test-staging-bucket"
    assert config.PUBLIC_S3_BUCKET_PROD == "test-prod-bucket"
