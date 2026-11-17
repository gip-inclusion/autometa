import json

import httpx
import pytest

from lib import agent_subagents

ENVOI = {"destination": "produit.opportunite", "title": "Export CSV", "text": "Trois demandes cette semaine."}
CLASSIFIEUR = {
    "type": "classifier",
    "model": "clef:27b",
    "question": "Est-ce une opportunité pour le produit ?",
    "threshold": 0.7,
}
EXTRACTION = {"type": "extraction", "model": "glm-5.2", "schema": {"produit": "string", "demandes": "integer"}}
RESUME = {"type": "summary", "model": "gemma4:31b", "max_length": 120}


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
        "delivery": ENVOI,
        "steps": [{"type": "classifier", "model": "clef:27b", "probability": 0.9123, "threshold": 0.7, "kept": True}],
        "calls": 1,
        "failure": None,
    }
    (url,), kwargs = ollama.call_args
    assert url == "https://ollama.com/v1/systemone"
    assert kwargs["headers"] == {"Authorization": "Bearer ollama-key"}
    assert kwargs["json"] == {
        "model": "clef:27b",
        "state": {"title": "Export CSV", "text": "Trois demandes cette semaine."},
        "questions": {"retenir": {"type": "noul", "instructions": CLASSIFIEUR["question"]}},
    }
    assert kwargs["timeout"]


def test_dod_10_extraction_constrains_the_chat_answer_to_the_declared_schema(ollama):
    ollama.return_value = chat(json.dumps({"produit": "emplois", "demandes": 3}))
    trace = agent_subagents.run_chain([EXTRACTION], ENVOI)
    assert trace["delivery"]["text"] == "Trois demandes cette semaine.\n\n- produit : emplois\n- demandes : 3"
    assert trace["steps"] == [
        {"type": "extraction", "model": "glm-5.2", "fields": {"produit": "emplois", "demandes": 3}}
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
    assert trace["delivery"] == {**ENVOI, "text": "Trois demandes d'export CSV."}
    assert trace["steps"] == [{"type": "summary", "model": "gemma4:31b", "length": 28}]
    (url,), kwargs = ollama.call_args
    assert url == "https://ollama.com/api/chat"
    assert "120 caractères au plus" in kwargs["json"]["messages"][0]["content"]
    assert kwargs["json"]["options"]["num_predict"] == 124


def test_dod_10_sub_agents_apply_in_the_configured_order_each_on_the_previous_output(ollama):
    ollama.side_effect = [chat(json.dumps({"produit": "emplois", "demandes": 3})), clef(0.8), chat("Résumé court.")]
    trace = agent_subagents.run_chain([EXTRACTION, CLASSIFIEUR, RESUME], ENVOI)
    assert [e["type"] for e in trace["steps"]] == ["extraction", "classifier", "summary"]
    assert ollama.call_args_list[1].kwargs["json"]["state"]["text"].endswith("- demandes : 3")
    assert "- demandes : 3" in ollama.call_args_list[2].kwargs["json"]["messages"][1]["content"]
    assert trace["delivery"]["text"] == "Résumé court."
    assert trace["calls"] == 3


def test_dod_10_a_classifier_under_its_threshold_stops_the_chain(ollama):
    ollama.return_value = clef(0.2)
    trace = agent_subagents.run_chain([CLASSIFIEUR, RESUME], ENVOI)
    assert ollama.call_count == 1
    assert trace["steps"][-1]["kept"] is False
    assert trace["delivery"] == ENVOI
    assert trace["calls"] == 1


@pytest.mark.parametrize(
    ("subagents", "responses", "expected"),
    [
        (
            [CLASSIFIEUR],
            [answer({"answers": {}})],
            "sous-agent 1 (classifier clef:27b) en échec : réponse illisible",
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
        (
            [CLASSIFIEUR, RESUME],
            [clef(0.9), httpx.ConnectError("refusé")],
            "sous-agent 2 (summary gemma4:31b) en échec",
        ),
        (
            [CLASSIFIEUR],
            [httpx.Response(200, text="<html>passerelle</html>", request=httpx.Request("POST", "https://ollama.com"))],
            "réponse qui n'est pas du JSON",
        ),
        (
            [CLASSIFIEUR, RESUME],
            [clef(0.9), httpx.Response(200, text="<html>", request=httpx.Request("POST", "https://ollama.com"))],
            "sous-agent 2 (summary gemma4:31b) en échec : réponse qui n'est pas du JSON",
        ),
        (
            [CLASSIFIEUR],
            [httpx.Response(503, request=httpx.Request("POST", "https://ollama.com/v1/systemone"))],
            "503",
        ),
    ],
)
def test_dod_10_a_failing_link_ends_the_chain_with_its_reason_and_no_content(ollama, subagents, responses, expected):
    ollama.side_effect = responses
    trace = agent_subagents.run_chain(subagents, ENVOI)
    assert expected in trace["failure"]
    assert "Trois demandes" not in trace["failure"]
    assert trace["calls"] == len(responses)


def test_dod_10_without_the_ollama_key_nothing_is_called(ollama, mocker):
    mocker.patch("lib.agent_subagents.config.OLLAMA_API_KEY", "")
    trace = agent_subagents.run_chain([CLASSIFIEUR], ENVOI)
    assert "OLLAMA_API_KEY absent" in trace["failure"]
    ollama.assert_not_called()


ETIQUETTEUR = {
    "type": "classifier",
    "model": "clef:27b",
    "labels": [
        {"name": "rapide", "question": "Est-ce faisable en moins d'une semaine ?"},
        {"name": "nouveaute", "question": "Est-ce une fonctionnalité nouvelle ?"},
        {"name": "terrain", "question": "Est-ce demandé par le terrain ?"},
    ],
    "threshold": 0.6,
}


def labels(**probabilities):
    return answer({"answers": {n: {"type": "noul", "noul": p} for n, p in probabilities.items()}})


def test_dod_17_a_labeller_asks_every_label_in_one_call_and_keeps_those_over_the_threshold(ollama):
    ollama.return_value = labels(rapide=0.91, nouveaute=0.2, terrain=0.6)
    trace = agent_subagents.run_chain([ETIQUETTEUR], ENVOI)
    assert ollama.call_count == 1
    questions = ollama.call_args.kwargs["json"]["questions"]
    assert questions == {e["name"]: {"type": "noul", "instructions": e["question"]} for e in ETIQUETTEUR["labels"]}
    assert trace["delivery"]["labels"] == ["rapide", "terrain"]
    assert trace["delivery"]["text"] == "Trois demandes cette semaine.\n\nÉtiquettes : rapide, terrain"
    assert trace["steps"] == [
        {
            "type": "classifier",
            "model": "clef:27b",
            "probabilities": {"rapide": 0.91, "nouveaute": 0.2, "terrain": 0.6},
            "threshold": 0.6,
            "labels": ["rapide", "terrain"],
        }
    ]


def test_dod_17_a_labeller_never_sets_aside_and_the_chain_goes_on(ollama):
    ollama.side_effect = [labels(rapide=0.1, nouveaute=0.1, terrain=0.1), chat("Court.")]
    trace = agent_subagents.run_chain([ETIQUETTEUR, RESUME], ENVOI)
    assert trace["steps"][0]["labels"] == []
    assert "Étiquettes : aucune" in ollama.call_args_list[1].kwargs["json"]["messages"][1]["content"]
    assert trace["delivery"]["text"] == "Court."
    assert trace["failure"] is None


def test_dod_17_the_same_model_serves_several_sub_agents_each_judging_one_production(ollama):
    filter = {**CLASSIFIEUR, "threshold": 0.5}
    ollama.side_effect = [clef(0.8), labels(rapide=0.7, nouveaute=0.9, terrain=0.1)]
    trace = agent_subagents.run_chain([filter, ETIQUETTEUR], ENVOI)
    assert [c.kwargs["json"]["model"] for c in ollama.call_args_list] == ["clef:27b", "clef:27b"]
    assert trace["delivery"]["labels"] == ["rapide", "nouveaute"]
    assert trace["calls"] == 2


def test_dod_17_a_label_missing_from_the_answer_is_a_failing_link(ollama):
    ollama.return_value = labels(rapide=0.9)
    trace = agent_subagents.run_chain([ETIQUETTEUR], ENVOI)
    assert "sous-agent 1 (classifier clef:27b) en échec : réponse illisible" in trace["failure"]
