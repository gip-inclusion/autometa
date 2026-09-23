"""Vectorise une requête de recherche avec le même modèle que les embeddings de messages."""

from model2vec import StaticModel

from web import config
from web.conversation_embeddings.generate_conversation_embeddings import normalize_embedding

_model = None


def embed_query(query: str) -> list[float]:
    """Vecteur normalisé de la requête, dans le même espace que les embeddings de messages."""
    global _model
    # Why: le modèle pèse plusieurs Mo et se charge une seule fois ; on le garde en mémoire du worker.
    if _model is None:
        _model = StaticModel.from_pretrained(config.EMBEDDING_MODEL)
    return normalize_embedding(_model.encode([query])[0])
