"""Prepare the message embedding model and embed search queries."""

import logging
import time

from model2vec import StaticModel

from web import config
from web.conversation_embeddings.generate_conversation_embeddings import normalize_embedding

logger = logging.getLogger(__name__)

_model = None
_MODEL_RETRY_DELAYS = (60, 60)


def prepare_embedding_model() -> None:
    """Load the model with bounded retries, using the local Hugging Face cache."""
    global _model
    if _model is not None:
        return

    started = time.perf_counter()
    logger.info("Preparing embedding model: %s", config.EMBEDDING_MODEL)
    max_attempts = len(_MODEL_RETRY_DELAYS) + 1
    for attempt in range(1, max_attempts + 1):
        try:
            _model = StaticModel.from_pretrained(config.EMBEDDING_MODEL, force_download=False)
        except Exception:
            # Why: this optional background task must not interrupt the app if model preparation fails.
            if attempt == max_attempts:
                logger.exception("Embedding model preparation failed after %d attempts", attempt)
                return
            delay = _MODEL_RETRY_DELAYS[attempt - 1]
            logger.warning(
                "Embedding model preparation attempt %d/%d failed; retrying in %d seconds",
                attempt,
                max_attempts,
                delay,
                exc_info=True,
            )
            time.sleep(delay)
            continue
        logger.info("Embedding model ready in %.2f seconds after %d attempt(s)", time.perf_counter() - started, attempt)
        return


def is_embedding_model_ready() -> bool:
    """Return whether the model is loaded and ready to embed queries."""
    return _model is not None


def embed_query(query: str) -> list[float]:
    """Embed a query with the prepared model and normalize the resulting vector."""
    return normalize_embedding(_model.encode([query])[0])
