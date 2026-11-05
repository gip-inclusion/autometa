import json

import httpx
import pytest

from lib import agent_subagents

ENVOI = {"destination": "produit.opportunite", "titre": "Export CSV", "texte": "Trois demandes cette semaine."}
CLASSIFIEUR = {
    "type": "classificateur",
    "modele": "clef:27b",
    "question": "Est-ce une opportunité pour le produit ?",
    "seuil": 0.7,
}
EXTRACTION = {"type": "extraction", "modele": "glm-5.2", "schema": {"produit": "texte", "demandes": "entier"}}
RESUME = {"type": "resume", "modele": "gemma4:31b", "longueur_max": 120}


def answer(body):
    return httpx.Response(200, json=body, request=httpx.Request("POST", "https://ollama.com"))


def clef(probability):
    return answer({"answers": {"retenir": {"type": "noul", "noul": probability}}})


def chat(content):
    return answer({"message": {"role": "assistant", "content": content}})


@pytest.fixture
def ollama(mocker):
    mocker.patch("lib.agent_subagents.config.OLLAMA_API_KEY", "ollama-key")
    mocker.patch("lib.agent_subagents.config.OLLAMA_REMOTE_BASE_URL", "https://ollama.com/")
    return mocker.patch("lib.agent_subagents.httpx.post")


def test_dod_10_classifier_asks_clef_on_ollama_cloud_for_the_probability_of_yes(ollama):
    ollama.return_value = clef(0.91234)
    trace = agent_subagents.run_chain([CLASSIFIEUR], ENVOI)
    assert trace == {
        "envoi": ENVOI,
        "etapes": [
            {"type": "classificateur", "modele": "clef:27b", "probabilite": 0.9123, "seuil": 0.7, "retenu": True}
        ],
        "appels": 1,
        "echec": None,
    }
    (url,), kwargs = ollama.call_args
    assert url == "https://ollama.com/v1/systemone"
    assert kwargs["headers"] == {"Authorization": "Bearer ollama-key"}
    assert kwargs["json"] == {
        "model": "clef:27b",
        "state": {"titre": "Export CSV", "texte": "Trois demandes cette semaine."},
        "questions": {"retenir": {"type": "noul", "instructions": CLASSIFIEUR["question"]}},
    }
    assert kwargs["timeout"]


def test_dod_10_extraction_constrains_the_chat_answer_to_the_declared_schema(ollama):
    ollama.return_value = chat(json.dumps({"produit": "emplois", "demandes": 3}))
    trace = agent_subagents.run_chain([EXTRACTION], ENVOI)
    assert trace["envoi"]["texte"] == "Trois demandes cette semaine.\n\n- produit : emplois\n- demandes : 3"
    assert trace["etapes"] == [
        {"type": "extraction", "modele": "glm-5.2", "champs": {"produit": "emplois", "demandes": 3}}
    ]
    (url,), kwargs = ollama.call_args
    assert url == "https://ollama.com/api/chat"
    assert kwargs["json"]["model"] == "glm-5.2"
    assert kwargs["json"]["stream"] is False
    assert kwargs["json"]["format"] == {
        "type": "object",
        "properties": {"produit": {"type": "string"}, "demandes": {"type": "integer"}},
        "required": ["produit", "demandes"],
        "additionalProperties": False,
    }
    assert kwargs["json"]["messages"][1] == {"role": "user", "content": "# Export CSV\n\nTrois demandes cette semaine."}


def test_dod_10_summary_rewrites_the_production_within_its_maximum_length(ollama):
    ollama.return_value = chat("  Trois demandes d'export CSV.  ")
    trace = agent_subagents.run_chain([RESUME], ENVOI)
    assert trace["envoi"] == {**ENVOI, "texte": "Trois demandes d'export CSV."}
    assert trace["etapes"] == [{"type": "resume", "modele": "gemma4:31b", "longueur": 28}]
    (url,), kwargs = ollama.call_args
    assert url == "https://ollama.com/api/chat"
    assert "120 caractères au plus" in kwargs["json"]["messages"][0]["content"]
    assert kwargs["json"]["options"]["num_predict"] == 124


def test_dod_10_sub_agents_apply_in_the_configured_order_each_on_the_previous_output(ollama):
    ollama.side_effect = [chat(json.dumps({"produit": "emplois", "demandes": 3})), clef(0.8), chat("Résumé court.")]
    trace = agent_subagents.run_chain([EXTRACTION, CLASSIFIEUR, RESUME], ENVOI)
    assert [e["type"] for e in trace["etapes"]] == ["extraction", "classificateur", "resume"]
    assert ollama.call_args_list[1].kwargs["json"]["state"]["texte"].endswith("- demandes : 3")
    assert "- demandes : 3" in ollama.call_args_list[2].kwargs["json"]["messages"][1]["content"]
    assert trace["envoi"]["texte"] == "Résumé court."
    assert trace["appels"] == 3


def test_dod_10_a_classifier_under_its_threshold_stops_the_chain(ollama):
    ollama.return_value = clef(0.2)
    trace = agent_subagents.run_chain([CLASSIFIEUR, RESUME], ENVOI)
    assert ollama.call_count == 1
    assert trace["etapes"][-1]["retenu"] is False
    assert trace["envoi"] == ENVOI
    assert trace["appels"] == 1


@pytest.mark.parametrize(
    ("outils", "responses", "expected"),
    [
        (
            [CLASSIFIEUR],
            [answer({"answers": {}})],
            "sous-agent 1 (classificateur clef:27b) en échec : réponse illisible",
        ),
        ([CLASSIFIEUR], [clef(None)], "réponse illisible"),
        ([CLASSIFIEUR], [answer(["pas un objet"])], "réponse illisible"),
        ([EXTRACTION], [chat("pas du json")], "sortie qui n'est pas du JSON"),
        ([EXTRACTION], [chat(json.dumps({"produit": "emplois"}))], "hors du schéma déclaré"),
        ([EXTRACTION], [chat(json.dumps({"produit": "emplois", "demandes": "3"}))], "hors du schéma déclaré"),
        ([EXTRACTION], [chat(json.dumps({"produit": "emplois", "demandes": True}))], "hors du schéma déclaré"),
        ([EXTRACTION], [chat(json.dumps(["emplois", 3]))], "hors du schéma déclaré"),
        ([RESUME], [chat("x" * 121)], "résumé de 121 caractères, attendu 1 à 120"),
        ([RESUME], [chat("   ")], "résumé de 0 caractères"),
        ([RESUME], [answer({"done": True})], "réponse illisible"),
        ([CLASSIFIEUR, RESUME], [clef(0.9), httpx.ConnectError("refusé")], "sous-agent 2 (resume gemma4:31b) en échec"),
        (
            [CLASSIFIEUR],
            [httpx.Response(503, request=httpx.Request("POST", "https://ollama.com/v1/systemone"))],
            "503",
        ),
    ],
)
def test_dod_10_a_failing_link_ends_the_chain_with_its_reason_and_no_content(ollama, outils, responses, expected):
    ollama.side_effect = responses
    trace = agent_subagents.run_chain(outils, ENVOI)
    assert expected in trace["echec"]
    assert "Trois demandes" not in trace["echec"]
    assert trace["appels"] == len(responses)


def test_dod_10_without_the_ollama_key_nothing_is_called(ollama, mocker):
    mocker.patch("lib.agent_subagents.config.OLLAMA_API_KEY", "")
    trace = agent_subagents.run_chain([CLASSIFIEUR], ENVOI)
    assert "OLLAMA_API_KEY absent" in trace["echec"]
    ollama.assert_not_called()
