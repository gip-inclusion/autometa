"""Config env-var wiring tests."""

import importlib

from web import config


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
