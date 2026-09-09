"""Config env-var wiring tests."""

import importlib

import pytest

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


def test_ollama_defaults_stay_local_until_a_key_is_given():
    assert config.OLLAMA_LOCAL_BASE_URL == "http://localhost:11434"
    assert config.OLLAMA_REMOTE_BASE_URL == "https://ollama.com"
    assert config.OLLAMA_MODEL == "glm-5.2"


@pytest.mark.parametrize(
    "api_key, expected",
    [("", "http://localhost:11434"), ("sk-abc", "https://ollama.com")],
)
def test_the_api_key_is_what_sends_conversations_off_premises(monkeypatch, api_key, expected):
    """Un déploiement ne doit jamais se mettre à sortir vers un tiers par héritage d'un défaut :
    seule une clé posée explicitement bascule la cible sur Ollama Cloud."""
    monkeypatch.setenv("OLLAMA_API_KEY", api_key)
    reloaded = importlib.reload(config)
    try:
        assert reloaded.OLLAMA_BASE_URL == expected
    finally:
        monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
        importlib.reload(config)
