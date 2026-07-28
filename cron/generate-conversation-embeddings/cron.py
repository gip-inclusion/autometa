"""Generate conversation message embeddings for the previous day. Periodic."""

import logging

from web import config
from web.conversation_embeddings.generate_conversation_embeddings import generate_embeddings

logger = logging.getLogger(__name__)


def main() -> None:
    if config.ENV.value != "prod":
        logger.info("AUTOMETA_ENV=%s (not prod); skipping conversation embedding generation", config.ENV.value)
        return

    generate_embeddings(
        limit=None,
        batch_size=config.EMBEDDING_BATCH_SIZE,
        days_ago=1,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
