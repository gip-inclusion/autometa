"""Generate missing or outdated conversation message embeddings. Periodic."""

import logging

from web import config
from web.conversation_embeddings.generate_conversation_embeddings import generate_embeddings

logger = logging.getLogger(__name__)


def main() -> None:
    generate_embeddings(
        limit=config.EMBEDDING_CRON_LIMIT,
        batch_size=config.EMBEDDING_BATCH_SIZE,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
