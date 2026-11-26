"""Vectorisation de la requête de recherche."""

import numpy as np
import pytest

from web import config
from web.conversation_embeddings import query_embedding


def test_preparation_loads_once_and_queries_reuse_the_normalized_model(mocker):
    mocker.patch.object(query_embedding, "_model", None)
    model = mocker.MagicMock()
    model.encode.return_value = np.array([[3.0, 4.0]])
    load = mocker.patch.object(query_embedding.StaticModel, "from_pretrained", return_value=model)
    sleep = mocker.patch.object(query_embedding.time, "sleep")

    assert not query_embedding.is_embedding_model_ready()
    query_embedding.prepare_embedding_model()
    assert query_embedding.is_embedding_model_ready()
    query_embedding.prepare_embedding_model()
    assert query_embedding.embed_query("pass IAE") == [0.6, 0.8]
    assert query_embedding.embed_query("pass IAE") == [0.6, 0.8]
    load.assert_called_once_with(config.EMBEDDING_MODEL, force_download=False)
    sleep.assert_not_called()


@pytest.mark.parametrize("failures, expected_delays", [(1, [60]), (2, [60, 60])])
def test_preparation_recovers_after_download_failures(mocker, caplog, failures, expected_delays):
    mocker.patch.object(query_embedding, "_model", None)
    model = mocker.MagicMock()
    load = mocker.patch.object(
        query_embedding.StaticModel,
        "from_pretrained",
        side_effect=[OSError("download failed") for _ in range(failures)] + [model],
    )

    def wait(delay):
        assert not query_embedding.is_embedding_model_ready()

    sleep = mocker.patch.object(query_embedding.time, "sleep", side_effect=wait)

    with caplog.at_level("INFO", logger=query_embedding.__name__):
        query_embedding.prepare_embedding_model()

    assert query_embedding.is_embedding_model_ready()
    assert query_embedding._model is model
    assert load.call_args_list == [
        mocker.call(config.EMBEDDING_MODEL, force_download=False) for _ in range(failures + 1)
    ]
    assert sleep.call_args_list == [mocker.call(delay) for delay in expected_delays]
    assert "retrying" in caplog.text
    assert "Embedding model ready" in caplog.text
    assert "Embedding model preparation failed after" not in caplog.text

    query_embedding.prepare_embedding_model()

    assert load.call_count == failures + 1
    assert sleep.call_count == failures


def test_failed_preparation_logs_error_and_keeps_model_unavailable(mocker, caplog):
    mocker.patch.object(query_embedding, "_model", None)
    load = mocker.patch.object(query_embedding.StaticModel, "from_pretrained", side_effect=OSError("download failed"))
    sleep = mocker.patch.object(query_embedding.time, "sleep")

    query_embedding.prepare_embedding_model()

    assert not query_embedding.is_embedding_model_ready()
    assert "Embedding model preparation failed after 3 attempts" in caplog.text
    assert load.call_args_list == [mocker.call(config.EMBEDDING_MODEL, force_download=False)] * 3
    assert sleep.call_args_list == [mocker.call(60), mocker.call(60)]
