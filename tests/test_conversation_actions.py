"""Ce que la page reçoit pour ses pastilles d'actions : les appels d'outils, sans ce qu'ils ont rendu en entier."""

import json

import pytest

from web.conversation_actions import light_messages, output_text

LONG = "é" * 600
SIGNAL = '[AUTOMETA:API:{"source": "matomo"}]\n'
CALLS = [{"source": "matomo", "method": "VisitsSummary.get", "url": "https://exemple.fr", "sql": None}]


def light(kind: str, content) -> object:
    stored = content if isinstance(content, str) else json.dumps(content)
    return light_messages([(7, kind, stored)])[0].get("content")


def test_questions_and_answers_come_as_their_place_in_the_thread_only():
    assert light_messages([(1, "user", ""), (2, "assistant", ""), (3, "system", "")]) == [
        {"id": 1, "type": "user"},
        {"id": 2, "type": "assistant"},
        {"id": 3, "type": "system"},
    ]


def test_a_call_keeps_its_short_inputs_and_the_start_of_its_long_ones():
    call = {"tool": "Write", "category": "Write: temp", "input": {"file_path": "/tmp/a", "content": LONG, "n": 3}}

    assert light("tool_use", call) == {
        "tool": "Write",
        "category": "Write: temp",
        "input": {"file_path": "/tmp/a", "content": "é" * 500, "n": 3},
        "capped": ["content"],
    }


@pytest.mark.parametrize(
    ("value", "sent", "capped"),
    [
        ({"a": [1, True, None], "texte": "é" * 600}, '{"a":[1,true,null],"texte":"' + "é" * 472, ["v"]),
        (["x" * 600], '["' + "x" * 498, ["v"]),
        ("x" * 500, "x" * 500, []),
        ({"a": 1}, {"a": 1}, []),
    ],
    ids=["objet", "liste", "juste-à-la-limite", "objet-court"],
)
def test_a_long_input_is_cut_as_the_page_would_write_it(value, sent, capped):
    cut = light("tool_use", {"tool": "T", "input": {"v": value}})

    assert (cut["input"]["v"], cut["capped"]) == (sent, capped)


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ("pas du json", "pas du json"),
        ("12", "12"),
        ('{"tool": "Bash", "input": "echo"}', {"tool": "Bash", "input": "echo"}),
        ('{"tool": "Bash"}', {"tool": "Bash"}),
    ],
    ids=["illisible", "pas-un-objet", "entrée-en-texte", "sans-entrée"],
)
def test_a_call_the_page_reads_otherwise_comes_as_stored(stored, expected):
    assert light("tool_use", stored) == expected


def test_a_result_gives_its_api_calls_and_the_start_of_its_text():
    result = {"output": {"tool": "Bash", "output": SIGNAL + "x" * 700}, "api_calls": CALLS}

    assert light("tool_result", result) == {"api_calls": CALLS, "output": "x" * 500, "output_capped": True}


@pytest.mark.parametrize(
    "stored",
    ["", "pas du json", '{"tool": "Bash", "output": "des mégaoctets"}', '{"output": "x", "api_calls": []}', "[1]"],
    ids=["non-lu", "illisible", "sans-appel-d-api", "appels-vides", "pas-un-objet"],
)
def test_a_result_without_api_calls_gives_nothing(stored):
    assert light("tool_result", stored) == {}


@pytest.mark.parametrize(
    ("output", "text"),
    [
        ("  texte  ", "texte"),
        ({"output": "dedans"}, "dedans"),
        ({"clé": 1}, '{\n  "clé": 1\n}'),
        ([{"type": "text", "text": "un"}, {"type": "image"}, "brut", {"text": "deux"}], "un\n\n\ndeux"),
        (SIGNAL + "avant\n" + SIGNAL + "après", "avant\naprès"),
        (None, "null"),
        (12, "12"),
    ],
    ids=["texte", "sortie-imbriquée", "objet", "blocs", "signaux", "rien", "nombre"],
)
def test_the_text_of_a_result_is_read_as_the_page_reads_it(output, text):
    assert output_text({"output": output}) == text
