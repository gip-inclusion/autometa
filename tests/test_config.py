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


def test_ollama_defaults_stay_local_until_a_key_is_given(monkeypatch):
    # Why: un .env de dev peut surcharger ces variables ; on teste les valeurs par défaut livrées,
    # donc on retire la surcharge et on neutralise le chargement du .env pendant le rechargement.
    for var in ("OLLAMA_REMOTE_BASE_URL", "OLLAMA_MODEL", "OLLAMA_SMALL_MODEL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: None)
    import web.config as c

    importlib.reload(c)
    try:
        assert c.OLLAMA_REMOTE_BASE_URL == "https://ollama.com"
        assert c.OLLAMA_MODEL == "glm-5.2"
        assert c.OLLAMA_SMALL_MODEL == "gemma4:31b-cloud"
    finally:
        monkeypatch.undo()
        importlib.reload(c)


@pytest.mark.parametrize(
    "api_key, local_url, expected",
    [
        ("", None, "http://localhost:11434"),
        ("", "http://gpu:11434", "http://gpu:11434"),
        ("sk-abc", "http://gpu:11434", "https://ollama.com"),
    ],
)
def test_the_api_key_is_what_sends_conversations_off_premises(monkeypatch, api_key, local_url, expected):
    """Seule une clé explicite sort vers Ollama Cloud ; OLLAMA_BASE_URL reste l'instance locale d'avant."""
    monkeypatch.setenv("OLLAMA_API_KEY", api_key)
    if local_url:
        monkeypatch.setenv("OLLAMA_BASE_URL", local_url)
    reloaded = importlib.reload(config)
    try:
        assert reloaded.OLLAMA_BASE_URL == expected
    finally:
        monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        importlib.reload(config)
