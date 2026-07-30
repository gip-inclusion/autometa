import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "generate_conversation_embeddings_cron",
    Path(__file__).resolve().parent.parent / "cron" / "generate-conversation-embeddings" / "cron.py",
)
cron = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cron)


@pytest.mark.parametrize("env_value", ["prod", "staging", "review", "dev"])
def test_main_generates_pending_embeddings_in_any_environment(mocker, env_value):
    """The cron can run in staging/review for pre-production measurement."""
    mocker.patch.object(cron.config, "ENV", type("Env", (), {"value": env_value})())
    mocker.patch.object(cron.config, "EMBEDDING_BATCH_SIZE", 17)
    mocker.patch.object(cron.config, "EMBEDDING_CRON_LIMIT", 250)
    generate_embeddings = mocker.patch.object(cron, "generate_embeddings")

    cron.main()

    generate_embeddings.assert_called_once_with(
        limit=250,
        batch_size=17,
    )
