"""Ce que la page montre d'un appel d'outil : sa pastille, ses valeurs coupées, et une valeur entière à la demande."""

import json
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from web.conversation_actions import displayed, output_text, pill, value_text

SHARED = json.loads((Path(__file__).parent / "fixtures" / "tool_values.json").read_text())
CONV = "abcd2345"
LONG = "é" * 600
SIGNAL = '[AUTOMETA:API:{"source": "matomo"}]\n'
CALLS = [{"source": "matomo", "method": "VisitsSummary.get", "url": "https://exemple.fr", "sql": None}]
TEMPLATES = Environment(
    loader=FileSystemLoader(Path(__file__).parent.parent / "web" / "templates"), autoescape=select_autoescape()
)


def described(use, result="", index: int = 1) -> dict:
    """The pill of a call stored as message 7 and of its result, message 8."""
    as_stored = [content if isinstance(content, str) else json.dumps(content) for content in (use, result)]
    return pill(CONV, index, (7, as_stored[0]), (8, as_stored[1]))


def values(shown: dict) -> dict:
    return {value["key"]: value for value in shown["values"]}


@pytest.mark.parametrize(
    ("category", "icon", "label"),
    [
        ("API: Matomo", "ri-cloud-line", "API Matomo"),
        ("Read: other", "ri-file-text-line", "notes.md"),
        ("Write: temp", "ri-file-add-line", "Écriture d'un fichier temporaire"),
        ("Shell: git", "ri-terminal-line", "Shell: git"),
        ("Inconnue", "ri-tools-line", "Inconnue"),
        (None, "ri-tools-line", "Action"),
    ],
    ids=["api", "lecture-nommée-par-son-fichier", "traduite", "gardée-telle-quelle", "sans-icône", "sans-catégorie"],
)
def test_a_pill_takes_the_icon_and_the_name_of_its_category(category, icon, label):
    shown = described({"tool": "T", "category": category, "input": {"file_path": "/tmp/dossier/notes.md"}})

    assert (shown["icon"], shown["label"], shown["summary"]) == (icon, label, None)
    assert (shown["index"], shown["message"], shown["data"]) == (1, 8, False)


@pytest.mark.parametrize(
    ("category", "calls", "label", "summary"),
    [
        ("API: Matomo", CALLS, "VisitsSummary.get", None),
        ("API: Metabase", [{"source": "metabase", "sql": "SELECT 1"}], "Requête SQL", None),
        ("API: Metabase", [{"source": "metabase"}], "API Metabase", None),
        (
            "Execute: script",
            [{"source": "matomo"}, {"source": "metabase"}, {"source": "matomo"}, {}],
            "Exécution d'un programme",
            "2 requêtes Matomo, 1 requête Metabase, 1 requête API",
        ),
    ],
    ids=["méthode", "sql", "api-sans-détail", "outil-qui-appelle-des-api"],
)
def test_a_call_that_reached_an_api_is_data_named_by_it_or_by_the_count_of_its_calls(category, calls, label, summary):
    shown = described({"tool": "T", "category": category, "input": {}}, {"output": "x", "api_calls": calls})

    assert (shown["label"], shown["summary"], shown["data"]) == (label, summary, True)


def test_a_knowledge_file_read_is_data_linked_to_its_page_without_its_path():
    shown = described({
        "tool": "Read",
        "category": "Read: knowledge",
        "input": {"file_path": "/app/knowledge/sites/dora.md", "n": 1},
    })

    assert (shown["data"], shown["label"]) == (True, "dora.md")
    assert shown["knowledge"] == {"path": "sites/dora.md", "name": "dora.md"}
    assert list(values(shown)) == ["N"]


def test_a_pill_shows_each_input_the_description_first_and_code_as_such():
    shown = described({"tool": "Bash", "input": {"command": "ls", "n": [1, None], "description": "Lister"}})

    assert [(v["key"], v["text"], v["description"], v["code"], v["cut"]) for v in shown["values"]] == [
        ("DESCRIPTION", "Lister", True, False, False),
        ("COMMAND", "ls", False, True, False),
        ("N", "[1,null]", False, False, False),
    ]


def test_a_long_value_is_cut_and_names_where_to_read_it_whole():
    call = {"tool": "Write", "input": {"content": LONG, "clé & co": {"a": "x" * 600}, "court": "x" * 500}}
    result = {"output": {"output": SIGNAL + "y" * 700}, "api_calls": CALLS}

    shown = values(described(call, result))

    assert [(key, value["cut"]) for key, value in shown.items()] == [
        ("CONTENT", True),
        ("CLÉ & CO", True),
        ("COURT", False),
        ("RÉSULTAT", True),
    ]
    assert shown["CONTENT"]["text"] == "é" * 500 + "..."
    assert shown["CLÉ & CO"]["text"] == '{"a":"' + "x" * 494 + "..."
    assert shown["RÉSULTAT"]["text"] == "y" * 500 + "..."
    assert shown["CONTENT"]["whole"] == f"/api/conversations/{CONV}/messages/7/value?input=content"
    assert shown["CLÉ & CO"]["whole"] == f"/api/conversations/{CONV}/messages/7/value?input=cl%C3%A9%20%26%20co"
    assert shown["RÉSULTAT"]["whole"] == f"/api/conversations/{CONV}/messages/8/value"


def test_the_result_shows_only_for_a_call_that_reached_an_api():
    assert "RÉSULTAT" not in values(described({"tool": "Bash", "input": {"command": "ls"}}, {"output": "sortie"}))


@pytest.mark.parametrize(
    ("call", "href", "text", "sql", "whole"),
    [
        (
            {"source": "matomo", "method": "M.get", "url": "https://exemple.fr/a?b=1"},
            "https://exemple.fr/a?b=1",
            "M.get",
            None,
            None,
        ),
        ({"source": "matomo", "method": "M.get", "url": "javascript:alert(1)"}, None, "M.get", None, None),
        ({"source": "matomo", "method": "M.get", "url": ["https://exemple.fr"]}, None, "M.get", None, None),
        ({"source": "metabase", "sql": "\\n  SELECT 1"}, None, "SELECT 1...", "SELECT 1", None),
        (
            {"source": "metabase", "sql": "S" * 300},
            None,
            "S" * 50 + "...",
            "S" * 200 + "...",
            f"/api/conversations/{CONV}/messages/8/value?sql=0",
        ),
        ({}, None, "View", None, None),
    ],
    ids=["lien", "adresse-dangereuse", "adresse-qui-n-est-pas-un-texte", "sql-court", "sql-long", "sans-détail"],
)
def test_an_api_call_is_linked_when_its_address_is_safe_and_shows_the_start_of_its_sql(call, href, text, sql, whole):
    shown = described({"tool": "T", "input": {}}, {"output": "", "api_calls": [call]})["calls"][0]

    assert (shown["href"], shown["text"], shown["sql"], shown["whole"]) == (href, text, sql, whole)
    assert shown["icon"] == ("ri-bar-chart-line" if call.get("source") == "matomo" else "ri-database-2-line")


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ("pas du json", [("INPUT", "pas du json")]),
        ("12", [("INPUT", "12")]),
        ('{"tool": "Bash", "input": "echo"}', [("INPUT", "echo")]),
        ('{"tool": "Bash"}', []),
        ('{"tool": "T", "input": {"n": NaN}}', [("N", "NaN")]),
    ],
    ids=["illisible", "pas-un-objet", "entrée-en-texte", "sans-entrée", "nan"],
)
def test_a_call_stored_otherwise_still_has_its_pill(stored, expected):
    shown = described(stored)

    assert [(value["key"], value["text"]) for value in shown["values"]] == expected
    assert shown["icon"] == "ri-tools-line"


@pytest.mark.parametrize(
    "stored",
    ["", "pas du json", "[1]", '{"output": "x", "api_calls": "aucun"}', '{"output": "x", "api_calls": [1, null]}'],
    ids=["non-lu", "illisible", "pas-un-objet", "appels-qui-ne-sont-pas-une-liste", "appels-illisibles"],
)
def test_a_result_without_api_calls_that_can_be_read_makes_no_data(stored):
    shown = described({"tool": "T", "input": {"a": 1}}, stored)

    assert (shown["data"], shown["calls"], list(values(shown))) == (False, [], ["A"])


def test_half_of_a_character_pair_is_shown_as_an_unknown_character():
    shown = described(
        '{"tool": "T", "input": {"coupé": "a \\ud83d", "entier": "\\ud83d\\ude00"}}',
        '{"output": "b \\ud83d", "api_calls": [{"source": "\\udc00"}]}',
    )

    assert [value["text"] for value in shown["values"]] == ["a �", "😀", "b �"]
    json.dumps(shown, ensure_ascii=False).encode()


def test_a_call_that_cannot_be_described_keeps_a_bare_pill(mocker, caplog):
    mocker.patch("web.conversation_actions.displayed", side_effect=RecursionError("trop profond"))

    shown = described({"tool": "T", "input": {"v": 1}}, index=3)

    assert shown == {"index": 3, "message": 8, "icon": "ri-tools-line", "label": "Action", "data": False}
    assert "Tool call 7 could not be described" in caplog.text


def rendered(shown: dict) -> str:
    return TEMPLATES.get_template("_action_pill.html").render(pill=shown)


def test_a_pill_is_written_with_what_the_page_filters_and_opens_it_by():
    call = {
        "tool": "Bash",
        "category": "Execute: script",
        "input": {"command": "x" * 600, "description": "<b>Calcul</b>"},
    }
    result = {"output": "<script>", "api_calls": [{"source": "metabase", "sql": "S" * 300, "url": "https://m.fr/q"}]}

    html = rendered(described(call, result, index=4))

    assert html.startswith('<div class="action-pill" data-action-index="4" data-msg-id="8" data-data>')
    assert (
        '<span class="action-pill-label-main" data-summary>1 requête Metabase</span>'
        '<span class="action-pill-label-sub">Exécution d&#39;un programme</span>'
    ) in html
    assert '<a href="https://m.fr/q" target="_blank" class="action-api-link">' in html
    assert f'<pre class="action-sql-preview">{"S" * 200}...</pre>' in html
    assert f'data-whole="/api/conversations/{CONV}/messages/8/value?sql=0" data-title="SQL" data-code>' in html
    assert '<div class="action-description">&lt;b&gt;Calcul&lt;/b&gt;</div>' in html
    assert (
        f'<div class="action-kv-key">COMMAND<button class="action-expand-btn" '
        f'data-whole="/api/conversations/{CONV}/messages/7/value?input=command" data-title="COMMAND" data-code>'
    ) in html
    assert '<div class="action-kv-value">&lt;script&gt;</div>' in html


@pytest.mark.parametrize(
    ("shown", "expected"),
    [
        (described({"tool": "Bash", "input": {}}), '<div class="action-pill filtered-out" data-action-index="1"'),
        (described({"tool": "Bash", "input": {}}), "<em>No details available</em>"),
        (described("illisible", index=2), '<span class="action-pill-label-main">Action</span>'),
        (
            described({"tool": "R", "category": "Read: knowledge", "input": {"file_path": "/x/knowledge/a/b.md"}}),
            '<a href="/knowledge/a/b.md" target="_blank" class="action-knowledge-link">',
        ),
        (described({"tool": "T", "input": {}}, {"api_calls": [{"url": "javascript:x"}]}), '<a target="_blank"'),
    ],
    ids=["hors-données", "sans-détail", "illisible", "fiche", "lien-sans-adresse"],
)
def test_a_pill_is_written_for_each_kind_of_call(shown, expected):
    assert expected in rendered(shown)


CALL = json.dumps({"tool": "T", "input": {"texte": LONG, "n": {"a": 1}}})
RESULT = json.dumps({"output": SIGNAL + "  sortie  ", "api_calls": [{"sql": "\\n SELECT 1"}, {"method": "M.get"}]})


@pytest.mark.parametrize(
    ("content", "input_key", "sql", "expected"),
    [
        (CALL, "texte", None, LONG),
        (CALL, "n", None, '{"a":1}'),
        (CALL, "absente", None, None),
        ("pas du json", "texte", None, None),
        (RESULT, None, 0, "SELECT 1"),
        (RESULT, None, 1, None),
        (RESULT, None, 2, None),
        (RESULT, None, -1, None),
        (RESULT, None, None, "sortie"),
        ("sortie brute", None, None, "sortie brute"),
        ('{"output": "coupé \\ud83d"}', None, None, "coupé �"),
    ],
    ids=[
        "entrée",
        "entrée-objet",
        "entrée-inconnue",
        "appel-illisible",
        "sql",
        "appel-sans-sql",
        "appel-inconnu",
        "rang-négatif",
        "résultat",
        "résultat-illisible",
        "demi-caractère",
    ],
)
def test_a_value_is_read_whole_from_its_stored_message(content, input_key, sql, expected):
    assert value_text(content, input_key, sql) == expected


@pytest.mark.parametrize("case", SHARED["outputs"], ids=[case["name"] for case in SHARED["outputs"]])
def test_the_text_of_a_result_is_read_as_the_page_used_to_read_it(case):
    assert output_text(case["result"]) == case["text"]


@pytest.mark.parametrize("case", SHARED["values"], ids=[case["name"] for case in SHARED["values"]])
def test_a_value_is_written_as_the_page_used_to_write_it(case):
    assert displayed(case["value"]) == case["text"]
