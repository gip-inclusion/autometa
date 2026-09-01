import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "generate_conversation_embeddings_cron",
    Path(__file__).resolve().parent.parent / "cron" / "generate-conversation-embeddings" / "cron.py",
)
cron = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cron)


def test_main_generates_pending_embeddings_with_configured_limits(mocker):
    mocker.patch.object(cron.config, "EMBEDDING_BATCH_SIZE", 17)
    mocker.patch.object(cron.config, "EMBEDDING_CRON_LIMIT", 250)
    generate_embeddings = mocker.patch.object(cron, "generate_embeddings")

    cron.main()

    generate_embeddings.assert_called_once_with(
        limit=250,
        batch_size=17,
    )
