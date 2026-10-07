"""Vectorisation de la requête de recherche."""

import numpy as np

from web.conversation_embeddings import query_embedding


def test_embed_query_charge_le_modele_une_fois_et_normalise(mocker):
    mocker.patch.object(query_embedding, "_model", None)
    model = mocker.MagicMock()
    model.encode.return_value = np.array([[3.0, 4.0]])
    load = mocker.patch.object(query_embedding.StaticModel, "from_pretrained", return_value=model)

    assert query_embedding.embed_query("pass IAE") == [0.6, 0.8]
    assert query_embedding.embed_query("pass IAE") == [0.6, 0.8]
    load.assert_called_once()
