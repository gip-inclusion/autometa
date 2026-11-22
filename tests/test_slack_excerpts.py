"""Extraits Slack d'un permalien : la même cible que la page, en texte que Slack ne peut pas lire comme du balisage."""

import json

import pytest

from lib import permalinks
from web import conversation_html, slack_excerpts
from web.stores.records import Conversation

CONV = "0a1b2c3d"
TABLE = "| Région | Candidatures |\n|---|---|\n| Bretagne | 12 |\n| Corse | 3 |\n"
ANSWER = f"Intro.\n\n## Méthode\n\nOn compte **tout**.\n\n## Résultats\n\n{TABLE}\n```mermaid\npie title Parts\n```\n"


def excerpt(mocker, messages, message_id, anchor=None, running=False):
    mocker.patch.object(conversation_html.store, "get_displayed_messages", return_value=messages)
    return slack_excerpts.excerpt(Conversation(id=CONV, needs_response=running), message_id, anchor)


def name(text, kind, rank=1):
    anchor = next(a for a in permalinks.anchors(text) if (a.kind, a.rank) == (kind, rank))
    return f"{kind}-{rank}-{anchor.digest}"


def shown(blocks):
    return "\n".join(e["text"] for b in blocks for e in ([b["text"]] if "text" in b else b["elements"]))


def test_a_conversation_address_alone_has_no_excerpt(mocker):
    assert excerpt(mocker, [(2, "assistant", ANSWER)], None) == []


def test_an_answer_permalink_shows_the_start_of_the_answer(mocker):
    blocks = excerpt(mocker, [(1, "user", "Q"), (2, "assistant", ANSWER)], 2)

    assert shown(blocks).startswith("Intro.\nMéthode\nOn compte tout.\nRésultats\n(tableau)\n(graphique)")


def test_an_answer_is_read_joined_as_on_the_page_without_its_front_matter(mocker):
    messages = [(2, "assistant", "---\ndate: 2026-11\n---\nDébut "), (3, "assistant", "et fin.")]

    assert shown(excerpt(mocker, messages, 3)) == "Début et fin."


def test_a_section_permalink_shows_its_title_and_its_text_only(mocker):
    blocks = excerpt(mocker, [(2, "assistant", ANSWER)], 2, name(ANSWER, "section", 1))

    assert shown(blocks) == "Méthode\nOn compte tout."


def test_a_table_permalink_shows_the_table_in_monospace_under_its_title(mocker):
    blocks = excerpt(mocker, [(2, "assistant", ANSWER)], 2, name(ANSWER, "table"))

    assert blocks[0]["text"] == {"type": "plain_text", "text": "Résultats", "emoji": False}
    assert blocks[1]["text"] == {
        "type": "mrkdwn",
        "verbatim": True,
        "text": "```\nRégion   | Candidatures\n---------+-------------\nBretagne | 12\nCorse    | 3\n```",
    }
    assert len(blocks) == 2


def test_a_chart_permalink_names_the_chart_without_an_image(mocker):
    blocks = excerpt(mocker, [(2, "assistant", ANSWER)], 2, name(ANSWER, "chart"))

    assert shown(blocks) == "Graphique : Parts"


def test_an_element_moved_to_another_rank_is_found_by_its_digest_as_on_the_page(mocker):
    moved = name(ANSWER, "section", 2).replace("section-2-", "section-7-")

    assert shown(excerpt(mocker, [(2, "assistant", ANSWER)], 2, moved)).startswith("Résultats\n(tableau)")


@pytest.mark.parametrize("anchor", ["section-1-000000", "table-9-abcdef", "figure-1-000000", "n'importe quoi"])
def test_an_element_that_is_not_in_the_message_falls_back_to_the_answer(mocker, anchor):
    assert shown(excerpt(mocker, [(2, "assistant", ANSWER)], 2, anchor)).startswith("Intro.")


def test_an_element_is_looked_for_in_its_own_message_of_a_joined_answer(mocker):
    messages = [(2, "assistant", "## Un\n\nPremier.\n"), (3, "assistant", "## Deux\n\nSecond.\n")]
    second = name("## Deux\n\nSecond.\n", "section")

    assert shown(excerpt(mocker, messages, 3, second)) == "Deux\nSecond."
    assert shown(excerpt(mocker, messages, 2, second)).startswith("Un\nPremier.\nDeux")


@pytest.mark.parametrize(
    "messages,message_id,running",
    [
        ([(1, "user", "Q"), (2, "assistant", "R")], 1, False),
        ([(1, "user", "Q"), (2, "assistant", "R")], 99, False),
        ([(1, "user", "Q"), (2, "tool_result", "secret")], 2, False),
        ([(1, "user", "Q"), (2, "assistant", "R"), (3, "user", "Q2"), (4, "assistant", "en cours")], 4, True),
    ],
    ids=["a question", "another conversation's message", "a tool result", "an answer of the running turn"],
)
def test_a_message_that_is_not_a_finished_answer_of_the_conversation_has_no_excerpt(
    mocker, messages, message_id, running
):
    assert excerpt(mocker, messages, message_id, running=running) == []


def test_a_finished_answer_keeps_its_excerpt_while_a_later_turn_runs(mocker):
    messages = [(1, "user", "Q"), (2, "assistant", "Finie."), (3, "user", "Q2"), (4, "assistant", "en cours")]

    assert shown(excerpt(mocker, messages, 2, running=True)) == "Finie."


def test_markdown_becomes_readable_text():
    text = slack_excerpts.plain_text(
        "# Titre *penché*\n\nUn [lien](https://x.example) et `du code`, ~~barré~~ <b>gras</b>\nsuite ![alt](i.png)\n\n"
        "- un\n- [ ] deux\n\n1. trois\n\n> cité\n\n```python\nprint(1)\n```\n"
    )

    assert text == "Titre penché\nUn lien et du code, barré gras suite alt\n• un\n• deux\n• trois\ncité\n(code)"


def test_a_long_text_is_cut_after_a_word_and_says_so(mocker):
    blocks = excerpt(mocker, [(2, "assistant", "mot " * 400)], 2)

    text = shown(blocks)
    assert text.endswith("mot …")
    assert len(text) <= 502
    assert "mo …" not in text


HOSTILE = (
    "<!channel> @here <@U123> #general *gras* _it_ ~x~ <https://evil.example|ici> https://evil.example ``` `x` &amp;"
)


def texts(node):
    if isinstance(node, dict):
        return ([node] if isinstance(node.get("text"), str) else []) + texts(list(node.values()))
    return [found for child in node for found in texts(child)] if isinstance(node, list) else []


@pytest.mark.parametrize(
    "text,kind",
    [
        (f"{HOSTILE}\n", None),
        (f"## {HOSTILE}\n\n{HOSTILE}\n", "section"),
        (f"## {HOSTILE}\n\n```mermaid\npie title {HOSTILE}\n```\n", "chart"),
    ],
    ids=["answer", "section", "chart"],
)
def test_text_excerpts_are_plain_text_slack_does_not_parse(mocker, text, kind):
    blocks = excerpt(mocker, [(2, "assistant", text)], 2, kind and name(text, kind))

    assert blocks
    assert {t["type"] for t in texts(blocks)} == {"plain_text"}


def test_a_table_cannot_leave_its_code_block_nor_carry_markup(mocker):
    hostile = HOSTILE.replace("|", " ")
    table = f"| {hostile} | b |\n|---|---|\n| ```` | `<!here>` |\n| \\`\\`\\` | <@U1> & co |\n"
    blocks = excerpt(mocker, [(2, "assistant", table)], 2, name(table, "table"))

    code = next(t for t in texts(blocks) if t["type"] == "mrkdwn")
    assert code["verbatim"] is True
    assert code["text"].startswith("```\n")
    assert code["text"].endswith("\n```")
    inside = code["text"][4:-4]
    assert "`" not in inside
    assert "<" not in inside
    assert ">" not in inside
    assert "&lt;!here&gt;" in inside
    assert "&amp; co" in inside
    assert {t["type"] for t in texts(blocks)} == {"mrkdwn"}


def test_a_table_the_parser_does_not_read_as_one_is_shown_as_plain_text(mocker):
    table = "| a <!channel> | b | c |\n|---|---|\n| 1 | 2 |\n"

    blocks = excerpt(mocker, [(2, "assistant", table)], 2, name(table, "table"))

    assert shown(blocks).startswith("| a | b | c |")
    assert {t["type"] for t in texts(blocks)} == {"plain_text"}


def test_a_large_table_is_cut_to_what_fits_and_says_what_is_left(mocker):
    header = "| " + " | ".join(f"colonne numéro {i}" for i in range(9)) + " |"
    cells = [[f"cellule {r}-{i}" for i in range(9)] for r in range(40)]
    body = "\n".join("| " + " | ".join(row) + " |" for row in cells)
    table = f"{header}\n|{'---|' * 9}\n{body}\n"

    blocks = excerpt(mocker, [(2, "assistant", table)], 2, name(table, "table"))

    lines = blocks[0]["text"]["text"].split("\n")[1:-1]
    assert len(lines) == 12
    assert max(len(line) for line in lines) <= 72
    assert lines[0].split(" | ") == [f"colonne numéro {i}" for i in range(3)]
    assert blocks[1]["elements"][0] == {"type": "plain_text", "text": "… 30 lignes et 6 colonnes de plus"}
    assert len(json.dumps(blocks[0])) < 3000


def test_a_long_cell_is_shortened(mocker):
    table = f"| a |\n|---|\n| {'x' * 60} |\n| un |\n"

    blocks = excerpt(mocker, [(2, "assistant", table)], 2, name(table, "table"))

    assert f"{'x' * 23}…\n" in blocks[0]["text"]["text"]
    assert shown(blocks).count("ligne") == 0
