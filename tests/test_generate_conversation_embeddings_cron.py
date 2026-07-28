import importlib.util
from pathlib import Path

import pytest

from web.environment import Environment

spec = importlib.util.spec_from_file_location(
    "generate_conversation_embeddings_cron",
    Path(__file__).resolve().parent.parent / "cron" / "generate-conversation-embeddings" / "cron.py",
)
cron = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cron)


def test_main_generates_previous_day_embeddings_on_prod(mocker):
    """Prod runs the previous-day embedding batch without a row limit."""
    mocker.patch.object(cron.config, "ENV", Environment.PROD)
    mocker.patch.object(cron.config, "EMBEDDING_BATCH_SIZE", 17)
    generate_embeddings = mocker.patch.object(cron, "generate_embeddings")

    cron.main()

    generate_embeddings.assert_called_once_with(
        limit=None,
        batch_size=17,
        days_ago=1,
    )


@pytest.mark.parametrize("env_value", [Environment.STAGING, Environment.REVIEW, Environment.DEV])
def test_main_skips_embedding_generation_outside_prod(mocker, env_value):
    """Non-prod environments discover the cron but skip embedding generation."""
    mocker.patch.object(cron.config, "ENV", env_value)
    generate_embeddings = mocker.patch.object(cron, "generate_embeddings")

    cron.main()

    generate_embeddings.assert_not_called()
