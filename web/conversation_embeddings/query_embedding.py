"""Prepare the message embedding model and embed search queries."""

import logging
import time

from model2vec import StaticModel

from web import config
from web.conversation_embeddings.generate_conversation_embeddings import normalize_embedding

logger = logging.getLogger(__name__)

_model = None


def prepare_embedding_model() -> None:
    """Load the model once, using the local Hugging Face cache when available."""
    global _model
    if _model is not None:
        return

    started = time.perf_counter()
    logger.info("Preparing embedding model: %s", config.EMBEDDING_MODEL)
    try:
        _model = StaticModel.from_pretrained(config.EMBEDDING_MODEL, force_download=False)
    except Exception:
        # Why: this optional background task must not interrupt the app if model preparation fails.
        logger.exception("Embedding model preparation failed")
        return
    logger.info("Embedding model ready in %.2f seconds", time.perf_counter() - started)


def is_embedding_model_ready() -> bool:
    """Return whether the model is loaded and ready to embed queries."""
    return _model is not None


def embed_query(query: str) -> list[float]:
    """Embed a query with the prepared model and normalize the resulting vector."""
    return normalize_embedding(_model.encode([query])[0])
