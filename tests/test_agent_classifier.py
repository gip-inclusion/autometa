import httpx
import pytest

from lib import agent_classifier

ENVOI = {"destination": "produit.opportunite", "titre": "Export CSV", "texte": "Trois demandes cette semaine."}
OUTIL = {"id": "classifieur.pertinence", "question": "Est-ce une opportunité pour le produit ?", "seuil": 0.7}


@pytest.fixture
def ollama(mocker):
    mocker.patch("lib.agent_classifier.config.OLLAMA_API_KEY", "ollama-key")
    mocker.patch("lib.agent_classifier.config.OLLAMA_REMOTE_BASE_URL", "https://ollama.com")
    post = mocker.patch("lib.agent_classifier.httpx.post")
    post.return_value = httpx.Response(
        200, json={"answers": {"retenir": {"type": "noul", "noul": 0.91234}}}, request=httpx.Request("POST", "x")
    )
    return post


def test_dod_10_each_production_gets_a_yes_probability_from_clef_on_ollama_cloud(ollama):
    assert agent_classifier.classify([OUTIL], ENVOI) == [
        {"modele": "classifieur.pertinence", "probabilite": 0.9123, "seuil": 0.7}
    ]
    (url,), kwargs = ollama.call_args
    assert url == "https://ollama.com/v1/systemone"
    assert kwargs["headers"] == {"Authorization": "Bearer ollama-key"}
    assert kwargs["json"] == {
        "model": "clef",
        "state": {"titre": "Export CSV", "texte": "Trois demandes cette semaine."},
        "questions": {"retenir": {"type": "noul", "instructions": OUTIL["question"]}},
    }
    assert kwargs["timeout"]


@pytest.mark.parametrize(
    "body", [{"answers": {}}, {"answers": {"retenir": {"type": "noul", "noul": None}}}, ["pas un objet"]]
)
def test_dod_10_unreadable_answer_is_an_error_never_a_default(ollama, body):
    ollama.return_value = httpx.Response(200, json=body, request=httpx.Request("POST", "x"))
    with pytest.raises(RuntimeError, match="illisible"):
        agent_classifier.classify([OUTIL], ENVOI)


def test_dod_10_without_the_ollama_key_nothing_is_called(ollama, mocker):
    mocker.patch("lib.agent_classifier.config.OLLAMA_API_KEY", "")
    with pytest.raises(RuntimeError, match="OLLAMA_API_KEY absent"):
        agent_classifier.classify([OUTIL], ENVOI)
    ollama.assert_not_called()
