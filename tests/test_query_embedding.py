"""Vectorisation de la requête de recherche."""

import numpy as np

from web import config
from web.conversation_embeddings import query_embedding


def test_preparation_loads_once_and_queries_reuse_the_normalized_model(mocker):
    mocker.patch.object(query_embedding, "_model", None)
    model = mocker.MagicMock()
    model.encode.return_value = np.array([[3.0, 4.0]])
    load = mocker.patch.object(query_embedding.StaticModel, "from_pretrained", return_value=model)

    assert not query_embedding.is_embedding_model_ready()
    query_embedding.prepare_embedding_model()
    assert query_embedding.is_embedding_model_ready()
    query_embedding.prepare_embedding_model()
    assert query_embedding.embed_query("pass IAE") == [0.6, 0.8]
    assert query_embedding.embed_query("pass IAE") == [0.6, 0.8]
    load.assert_called_once_with(config.EMBEDDING_MODEL, force_download=False)


def test_failed_preparation_logs_error_and_keeps_model_unavailable(mocker, caplog):
    mocker.patch.object(query_embedding, "_model", None)
    load = mocker.patch.object(query_embedding.StaticModel, "from_pretrained", side_effect=OSError("download failed"))

    query_embedding.prepare_embedding_model()

    assert not query_embedding.is_embedding_model_ready()
    assert "Embedding model preparation failed" in caplog.text
    load.assert_called_once_with(config.EMBEDDING_MODEL, force_download=False)
