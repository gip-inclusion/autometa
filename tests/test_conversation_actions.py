"""Ce que la page reçoit pour ses pastilles d'actions : les appels d'outils, sans ce qu'ils ont rendu en entier."""

import json
from pathlib import Path

import pytest

from web.conversation_actions import actions_json, displayed, output_text

# Why: les mêmes cas sont joués dans la page (browser/test_server_rendering.py), pour que le début d'un résultat
# écrit ici et sa lecture par actions.js ne s'écartent pas.
SHARED = json.loads((Path(__file__).parent / "fixtures" / "tool_values.json").read_text())
LONG = "é" * 600
SIGNAL = '[AUTOMETA:API:{"source": "matomo"}]\n'
CALLS = [{"source": "matomo", "method": "VisitsSummary.get", "url": "https://exemple.fr", "sql": None}]


def sent(messages: list[tuple[int, str, str]]) -> list[dict]:
    return json.loads(actions_json("abcd2345", messages, [], []))["messages"]


def light(kind: str, content) -> object:
    return sent([(7, kind, content if isinstance(content, str) else json.dumps(content))])[0].get("content")


def test_the_body_names_the_conversation_its_messages_and_what_waits():
    body = json.loads(actions_json("abcd2345", [(1, "user", "")], [{"id": "a", "content": "é"}], [{"id": "b"}]))

    assert body == {
        "id": "abcd2345",
        "messages": [{"id": 1, "type": "user"}],
        "queue": [{"id": "a", "content": "é"}],
        "returned": [{"id": "b"}],
    }


def test_questions_and_answers_come_as_their_place_in_the_thread_only():
    assert sent([(1, "user", ""), (2, "assistant", ""), (3, "system", "")]) == [
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
    ("value", "kept", "capped"),
    [
        ({"a": [1, True, None], "texte": "é" * 600}, '{"a":[1,true,null],"texte":"' + "é" * 472, ["v"]),
        (["x" * 600], '["' + "x" * 498, ["v"]),
        ("x" * 500, "x" * 500, []),
        ({"a": 1}, {"a": 1}, []),
    ],
    ids=["objet", "liste", "juste-à-la-limite", "objet-court"],
)
def test_a_long_input_is_cut_as_the_page_would_write_it(value, kept, capped):
    cut = light("tool_use", {"tool": "T", "input": {"v": value}})

    assert (cut["input"]["v"], cut["capped"]) == (kept, capped)


def test_a_path_cut_short_comes_with_the_name_of_its_file():
    path = "/tmp/" + "dossier/" * 80 + "rapport final.md"

    read = light("tool_use", {"tool": "Read", "category": "Read: other", "input": {"file_path": path}})

    assert (read["input"]["file_path"], read["file_name"]) == (path[:500], "rapport final.md")
    assert "file_name" not in light("tool_use", {"tool": "Read", "input": {"file_path": "/tmp/court.md"}})


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ("pas du json", "pas du json"),
        ("12", "12"),
        ('{"tool": "Bash", "input": "echo"}', {"tool": "Bash", "input": "echo"}),
        ('{"tool": "Bash"}', {"tool": "Bash"}),
        ('{"tool": "T", "input": {"n": NaN}}', '{"tool": "T", "input": {"n": NaN}}'),
        ('{"tool": "T", "input": {"n": -Infinity}}', '{"tool": "T", "input": {"n": -Infinity}}'),
    ],
    ids=["illisible", "pas-un-objet", "entrée-en-texte", "sans-entrée", "nan", "infini"],
)
def test_a_call_the_page_reads_otherwise_comes_as_stored(stored, expected):
    assert light("tool_use", stored) == expected


def test_a_result_gives_its_api_calls_and_the_start_of_its_text():
    result = {"output": {"tool": "Bash", "output": SIGNAL + "x" * 700}, "api_calls": CALLS}

    assert light("tool_result", result) == {"api_calls": CALLS, "output": "x" * 500, "output_capped": True}


def test_the_start_of_a_result_keeps_the_spaces_it_ends_with():
    result = {"output": "x" * 498 + "  " + "y" * 10, "api_calls": CALLS}

    assert light("tool_result", result)["output"] == "x" * 498 + "  "


@pytest.mark.parametrize(
    "stored",
    [
        "",
        "pas du json",
        '{"tool": "Bash", "output": "des mégaoctets"}',
        '{"output": "x", "api_calls": []}',
        "[1]",
        '{"output": NaN, "api_calls": [{"source": "matomo"}]}',
    ],
    ids=["non-lu", "illisible", "sans-appel-d-api", "appels-vides", "pas-un-objet", "nan"],
)
def test_a_result_without_api_calls_the_page_can_read_gives_nothing(stored):
    assert light("tool_result", stored) == {}


@pytest.mark.parametrize(
    ("kind", "stored", "expected"),
    [
        ("tool_use", '{"tool": "T", "input": {"texte": "coupé \\ud83d"}}', {"texte": "coupé \ufffd"}),
        ("tool_use", '{"tool": "T", "input": {"texte": "entier \\ud83d\\ude00"}}', {"texte": "entier 😀"}),
        ("tool_result", '{"output": "coupé \\ud83d", "api_calls": [{"source": "\\udc00"}]}', "coupé \ufffd"),
    ],
    ids=["demi-caractère-en-entrée", "caractère-entier", "demi-caractère-en-résultat"],
)
def test_half_of_a_character_pair_is_sent_as_an_unknown_character(kind, stored, expected):
    body = actions_json("abcd2345", [(7, kind, stored)], [], [])

    body.encode()
    content = json.loads(body)["messages"][0]["content"]
    assert (content["input"] if kind == "tool_use" else content["output"]) == expected


def test_a_message_that_cannot_be_made_light_leaves_the_others_as_they_are(mocker, caplog):
    mocker.patch("web.conversation_actions.displayed", side_effect=[RecursionError("trop profond"), "court"])
    call = json.dumps({"tool": "T", "input": {"v": 1}})

    first, result, second = sent([(1, "tool_use", call), (2, "tool_result", ""), (3, "tool_use", call)])

    assert (first["content"], result["content"]) == (call, {})
    assert second["content"] == {"tool": "T", "input": {"v": 1}, "capped": []}
    assert "Message 1 could not be made light" in caplog.text


@pytest.mark.parametrize("case", SHARED["outputs"], ids=[case["name"] for case in SHARED["outputs"]])
def test_the_text_of_a_result_is_read_as_the_page_reads_it(case):
    assert output_text(case["result"]) == case["text"]


@pytest.mark.parametrize("case", SHARED["values"], ids=[case["name"] for case in SHARED["values"]])
def test_a_value_is_written_as_the_page_writes_it(case):
    assert displayed(case["value"]) == case["text"]
