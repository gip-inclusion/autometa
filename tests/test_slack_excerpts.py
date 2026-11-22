"""Extraits Slack d'un permalien : la même cible que la page, en texte que Slack ne peut pas lire comme du balisage."""

import json

import pytest

from lib import permalinks
from web import conversation_html, slack_excerpts
from web.stores.records import Conversation

CONV = "0a1b2c3d"
TABLE = "| Région | Candidatures |\n|---|---|\n| Bretagne | 12 |\n| Corse | 3 |\n"
ANSWER = f"Intro.\n\n## Méthode\n\nOn compte **tout**.\n\n## Résultats\n\n{TABLE}\n```mermaid\npie title Parts\n```\n"


def excerpt(mocker, messages, message_id, anchor=None, running=False, native=False):
    """L'extrait tel que Slack le reçoit, ses tableaux en chasse fixe, ou en bloc table avec `native`."""
    mocker.patch.object(conversation_html.store, "get_thread_messages", return_value=messages)
    blocks = slack_excerpts.excerpt(Conversation(id=CONV, needs_response=running), message_id, anchor)
    return slack_excerpts.with_tables(blocks, native)


def name(text, kind, rank=1):
    anchor = next(a for a in permalinks.anchors(text) if (a.kind, a.rank) == (kind, rank))
    return f"{kind}-{rank}-{anchor.digest}"


def shown(blocks):
    texts = []
    for block in blocks:
        if block["type"] == "chart":
            texts.append({"text": f"[graphique {block['title']}]"})
        else:
            texts += [block["text"]] if "text" in block else block["elements"]
    return "\n".join(text["text"] for text in texts)


def test_a_conversation_address_alone_has_no_excerpt(mocker):
    assert excerpt(mocker, [(2, "assistant", ANSWER)], None) == []


def test_an_answer_permalink_shows_the_start_of_the_answer_then_its_first_figure(mocker):
    blocks = excerpt(mocker, [(1, "user", "Q"), (2, "assistant", ANSWER)], 2)

    assert blocks[0]["text"]["text"] == "Intro.\nMéthode\nOn compte tout.\nRésultats"
    assert blocks[1]["text"]["text"].startswith("```\nRégion   | Candidatures\n")
    assert len(blocks) == 2


def test_an_answer_whose_first_figure_is_a_chart_shows_the_chart(mocker):
    text = f"Voici.\n\n```mermaid\npie title Parts\n```\n\n{TABLE}"

    blocks = excerpt(mocker, [(2, "assistant", text)], 2)

    assert blocks[1:] == [{"type": "chart", "source": "pie title Parts", "title": "Parts"}]


def test_a_figure_past_the_shown_start_of_the_answer_is_not_shown(mocker):
    text = f"{'mot ' * 200}\n\n{TABLE}"

    blocks = excerpt(mocker, [(2, "assistant", text)], 2)

    assert [block["text"]["type"] for block in blocks] == ["plain_text"]


def test_a_large_table_in_an_answer_says_how_many_rows_are_left(mocker):
    rows = "".join(f"| ligne {n} | {n} |\n" for n in range(300))
    text = f"Voici.\n\n| a | b |\n|---|---|\n{rows}"

    blocks = excerpt(mocker, [(2, "assistant", text)], 2)

    assert blocks[-1]["elements"][0]["text"] == "… 290 lignes de plus"


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


def test_a_chart_permalink_gives_the_chart_to_draw_with_its_title(mocker):
    blocks = excerpt(mocker, [(2, "assistant", ANSWER)], 2, name(ANSWER, "chart"))

    assert blocks == [{"type": "chart", "source": "pie title Parts", "title": "Parts"}]


def test_an_element_moved_to_another_rank_is_found_by_its_digest_as_on_the_page(mocker):
    moved = name(ANSWER, "section", 2).replace("section-2-", "section-7-")

    assert shown(excerpt(mocker, [(2, "assistant", ANSWER)], 2, moved)).startswith("Résultats\n```\nRégion")


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


def test_markdown_becomes_readable_text_without_code_options_or_figures():
    lines, figures = slack_excerpts.read(
        "# Titre *penché*\n\nUn [lien](https://x.example) et `du code`, ~~barré~~ <b>gras</b>\nsuite ![alt](i.png)\n\n"
        "- un\n- [ ] deux\n\n1. trois\n\n> cité\n\n```python\nprint(1)\n```\n\n"
        f"{TABLE}\n```mermaid\npie\n```\n\n```options\nOui\nNon | Non, merci\n```\n\n    indenté\n\nFin.\n"
    )

    assert lines == [
        "Titre penché",
        "Un lien et du code, barré gras suite alt",
        "• un",
        "• deux",
        "• trois",
        "cité",
        "Fin.",
    ]
    assert [(kind, line) for _, kind, line in figures] == [("table", 16), ("chart", 21)]


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
    assert {t["type"] for t in texts(blocks)} <= {"plain_text"}
    assert all(block["type"] in ("section", "chart") for block in blocks)


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


@pytest.mark.parametrize(
    "text,kind",
    [
        (f"## {'T' * 10000}\n\nTexte.\n", "section"),
        (f"```mermaid\npie title {'X' * 5000}\n```\n", "chart"),
        (f"**{'G' * 5000}**\n\n{TABLE}", "table"),
    ],
)
def test_a_title_of_any_length_is_cut_well_under_what_slack_accepts(mocker, text, kind):
    blocks = excerpt(mocker, [(2, "assistant", text)], 2, name(text, kind))

    assert (blocks[0].get("title") or blocks[0]["text"]["text"].split("\n")[0]).endswith("…")
    assert all(len(t["text"]) < 700 for t in texts(blocks))
    assert len(blocks[0].get("title", "")) < 160


def test_a_table_full_of_characters_to_escape_stays_under_slack_text_limit(mocker):
    rows = "".join(f"| {'&' * 22} | {'<' * 22} | {'>' * 22} |\n" for _ in range(30))
    table = f"| a | b | c |\n|---|---|---|\n{rows}"

    blocks = excerpt(mocker, [(2, "assistant", table)], 2, name(table, "table"))

    code = blocks[0]["text"]["text"]
    assert len(code) <= 3000
    assert code.endswith("\n```")
    drawn = code.count("\n") - 3
    assert blocks[1]["elements"][0]["text"] == f"… {30 - drawn} lignes de plus"


def test_two_tables_the_parser_reads_where_the_page_shows_one_do_not_break_the_excerpt(mocker):
    text = "- | a | b |\n  |---|---|\n  | 1 | 2 |\n| x |\n|---|\n| y |\n"
    anchors = [a for a in permalinks.anchors(text) if a.kind == "table"]

    for anchor in anchors:
        assert excerpt(mocker, [(2, "assistant", text)], 2, f"table-{anchor.rank}-{anchor.digest}")


def test_rows_of_another_length_than_the_header_are_not_drawn_as_a_table():
    assert slack_excerpts.table_rows("| a | b |\n|---|---|\n| 1 | 2 |\n\n| x |\n|---|\n| y |\n") == [
        ["a", "b"],
        ["1", "2"],
    ]


def test_a_huge_cell_does_not_hold_the_server(mocker):
    table = f"| a |\n|---|\n| {'[' * 1_000_000} |\n"
    anchor = next(a for a in permalinks.anchors(table) if a.kind == "table")
    parse = mocker.spy(slack_excerpts.ANSWER, "parse")

    slack_excerpts.table_blocks(anchor)

    assert len(parse.call_args.args[0]) < 13_000


@pytest.mark.parametrize(
    "text",
    [
        "<details>\n<summary>x</summary>\n## Dans du HTML\ncontenu\n</details>\n\nSuite.\n",
        "<!-- c\n\n## Avalé par un commentaire\n\ntexte\n",
        "    ## Dans du code\n\ntexte\n",
    ],
)
def test_an_element_the_page_does_not_link_gets_the_answer_excerpt_as_on_the_page(mocker, text):
    messages = [(2, "assistant", text)]
    sliced = [a for a in permalinks.anchors(text) if a.kind == "section"]
    html = str(conversation_html.thread(CONV, messages)["blocks"][0]["html"])

    assert "data-anchor=" not in html
    for anchor in sliced:
        named = excerpt(mocker, messages, 2, f"section-{anchor.rank}-{anchor.digest}")
        assert named == excerpt(mocker, messages, 2)


def test_a_section_runs_to_the_next_title_of_its_level_across_joined_messages_as_the_page_outlines_it(mocker):
    first = "Intro\n\n## Résultats\n"
    messages = [
        (2, "assistant", first),
        (
            3,
            "assistant",
            "\nLe texte est dans le message suivant.\n\n### Détail\n\nPrécision.\n\n## Autre\n\nHors section.\n",
        ),
    ]

    shown_text = shown(excerpt(mocker, messages, 2, name(first, "section")))

    assert shown_text == "Résultats\nLe texte est dans le message suivant.\nDétail\nPrécision."


def test_a_section_under_front_matter_is_read_at_its_own_lines(mocker):
    text = "---\ndate: 2026-11\n---\n# Rapport\n\nCorps.\n\n# Annexe\n\nFin.\n"

    assert shown(excerpt(mocker, [(2, "assistant", text)], 2, name(text, "section", 2))) == "Annexe\nFin."


def test_a_title_inside_a_list_ends_its_section_with_the_list(mocker):
    text = "- item\n  ## Dans la liste\n\n  dedans\n\nAprès la liste.\n"
    messages = [(2, "assistant", text)]

    assert 'data-anchor="2-section-1"' in str(conversation_html.thread(CONV, messages)["blocks"][0]["html"])
    assert shown(excerpt(mocker, messages, 2, name(text, "section"))) == "Dans la liste\ndedans"


@pytest.mark.parametrize(
    "markdown,expected",
    [
        ("a<br>b", ["a b"]),
        ("- | a |\n  |---|\n  | 1 |\n\nAprès.\n", ["Après."]),
        ("- ```\n  x\n  ```\n- deux\n", ["• deux"]),
    ],
)
def test_text_keeps_its_words_apart_and_its_bullets_on_their_items(markdown, expected):
    assert slack_excerpts.read(markdown)[0] == expected


BIDI = "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"


def test_writing_direction_characters_are_removed_from_text_and_tables(mocker):
    text = f"## Titre{BIDI}\n\nTexte{BIDI} suite.\n\n| a{BIDI} | b |\n|---|---|\n| 1{BIDI} | 2 |\n"

    section = shown(excerpt(mocker, [(2, "assistant", text)], 2, name(text, "section")))
    table = json.dumps(excerpt(mocker, [(2, "assistant", text)], 2, name(text, "table")), ensure_ascii=False)

    assert section.startswith("Titre\nTexte suite.")
    assert not set(BIDI) & set(section + table)


def test_an_element_of_an_answer_too_long_to_render_cheaply_gets_no_excerpt(mocker, caplog):
    caplog.set_level("INFO")
    text = f"## Titre\n\n{'mot ' * 75_000}\n"
    render = mocker.spy(conversation_html, "answer_block")

    assert excerpt(mocker, [(2, "assistant", text)], 2, name(text, "section")) == []
    render.assert_not_called()
    assert "trop longue pour un extrait" in caplog.text
    assert shown(excerpt(mocker, [(2, "assistant", text)], 2)).startswith("Titre\nmot mot")


def test_an_answer_just_under_the_length_limit_keeps_its_element_excerpts(mocker):
    text = f"## Titre\n\n{'mot ' * 74_000}\n"

    assert shown(excerpt(mocker, [(2, "assistant", text)], 2, name(text, "section"))).startswith("Titre\nmot mot")


def cells(table):
    return [[cell["text"] for cell in row] for row in table["rows"]]


def test_a_table_is_given_to_slack_as_a_table_block_of_raw_text_cells(mocker):
    blocks = excerpt(mocker, [(2, "assistant", ANSWER)], 2, name(ANSWER, "table"), native=True)

    assert blocks[0]["text"]["text"] == "Résultats"
    assert blocks[1] == {
        "type": "table",
        "column_settings": [{"is_wrapped": True}, {"align": "right"}],
        "rows": [
            [{"type": "raw_text", "text": "Région"}, {"type": "raw_text", "text": "Candidatures"}],
            [{"type": "raw_text", "text": "Bretagne"}, {"type": "raw_text", "text": "12"}],
            [{"type": "raw_text", "text": "Corse"}, {"type": "raw_text", "text": "3"}],
        ],
    }
    assert len(blocks) == 2


def test_an_answer_shows_its_first_table_as_a_table_block_too(mocker):
    blocks = excerpt(mocker, [(2, "assistant", ANSWER)], 2, native=True)

    assert [block["type"] for block in blocks] == ["section", "table"]


@pytest.mark.parametrize(
    "column,right",
    [
        (["8 412", "9\u202f104", "-3,5", "12 %", "1.5", "45 €", "−2"], True),
        (["12", "", "7"], True),
        (["12", "n/a"], False),
        (["2026-04", "2026-05"], False),
        (["Bretagne", "Corse"], False),
        (["", ""], True),
    ],
)
def test_a_column_of_numbers_is_aligned_right_and_any_other_wraps(mocker, column, right):
    table = "| a | b |\n|---|---|\n" + "".join(f"| x | {cell} |\n" for cell in column)

    block = excerpt(mocker, [(2, "assistant", table)], 2, name(table, "table"), native=True)[0]

    assert block["column_settings"] == [{"is_wrapped": True}, {"align": "right"} if right else {"is_wrapped": True}]


def test_a_table_block_holds_twenty_rows_and_twenty_columns_and_says_what_is_left(mocker):
    header = "| " + " | ".join(f"c{i}" for i in range(25)) + " |"
    body = [[f"l{r}c{i}" for i in range(25)] for r in range(60)]
    drawn = ["| " + " | ".join(row) + " |" for row in body]
    table = "\n".join([header, "|" + "---|" * 25, *drawn, ""])

    blocks = excerpt(mocker, [(2, "assistant", table)], 2, name(table, "table"), native=True)

    shown = cells(blocks[0])
    assert len(shown) == 21
    assert {len(row) for row in shown} == {20}
    assert shown[0][:2] == ["c0", "c1"]
    assert shown[20][19] == "l19c19"
    assert len(blocks[0]["column_settings"]) == 20
    assert blocks[1]["elements"][0]["text"] == "… 40 lignes et 5 colonnes de plus"


def test_a_table_block_stays_under_the_characters_slack_accepts_and_counts_the_rows_it_drops(mocker):
    wide = " | ".join("mot " * 30 for _ in range(10))
    table = f"| {' | '.join('abcdefghij')} |\n|{'---|' * 10}\n" + f"| {wide} |\n" * 30

    blocks = excerpt(mocker, [(2, "assistant", table)], 2, name(table, "table"), native=True)

    shown = cells(blocks[0])
    assert sum(len(cell) for row in shown for cell in row) <= 10_000
    assert all(len(cell) <= 82 for row in shown for cell in row)
    assert shown[1][0].endswith("mot …")
    assert blocks[1]["elements"][0]["text"] == f"… {30 - (len(shown) - 1)} lignes de plus"
    assert 1 < len(shown) < 21


def test_a_table_block_cell_cannot_mention_and_carries_no_direction_character(mocker):
    table = f"| a{BIDI} | b |\n|---|---|\n| \\<!channel> @here | @channel <@U1> |\n|  | x |\n"

    blocks = excerpt(mocker, [(2, "assistant", table)], 2, name(table, "table"), native=True)

    shown = cells(blocks[0])
    assert shown[0] == ["a", "b"]
    assert shown[1] == ["<\u200b!channel> @\u200bhere", "@\u200bchannel <\u200b@\u200bU1>"]
    assert shown[2] == [" ", "x"]
    assert {cell["type"] for row in blocks[0]["rows"] for cell in row} == {"raw_text"}


def test_a_table_carries_both_forms_until_the_listener_chooses(mocker):
    mocker.patch.object(conversation_html.store, "get_thread_messages", return_value=[(2, "assistant", TABLE)])

    blocks = slack_excerpts.excerpt(Conversation(id=CONV), 2, name(TABLE, "table"))

    assert [block["type"] for block in blocks] == ["table_excerpt"]
    assert [block["type"] for block in slack_excerpts.with_tables(blocks, True)] == ["table"]
    assert slack_excerpts.with_tables(blocks, False)[0]["text"]["text"].startswith("```\n")


@pytest.mark.parametrize(
    "text,limit,shown",
    [
        ("un deux trois", 20, "un deux trois"),
        ("un deux trois", 8, "un …"),
        ("   \n  suite", 4, " …"),
        (" " * 10, 4, " …"),
    ],
    ids=["short", "cut after a word", "blank start", "blank only"],
)
def test_a_text_is_cut_after_a_word_even_when_its_start_is_blank(text, limit, shown):
    assert slack_excerpts.shortened(text, limit) == shown


def turn(*answers):
    """Un tour dont chaque réponse est suivie d'un appel d'outil, comme l'agent les sépare."""
    messages = [(1, "user", "Question")]
    for text in answers:
        messages += [(len(messages) + 1, "assistant", text), (len(messages) + 2, "tool_use", "{}")]
    return messages


@pytest.mark.parametrize(
    ("later", "expected"),
    [
        (["La suite, sans titre.\n"], "Une\nTexte.\nLa suite, sans titre."),
        (["Suite.\n\n### Dessous\n\nDétail.\n"], "Une\nTexte.\nSuite.\nDessous\nDétail."),
        (["Suite.\n\n## Deux\n\nAutre.\n"], "Une\nTexte.\nSuite."),
        (["## Deux\n\nAutre.\n"], "Une\nTexte."),
        (["", "Encore.\n", "# Haut\n\nFin.\n", "Après.\n"], "Une\nTexte.\nEncore."),
        (["---\ntitle: x\n---\nCorps du rapport.\n"], "Une\nTexte.\nCorps du rapport."),
    ],
    ids=["text", "lower title", "same level after text", "same level at once", "across several", "report"],
)
def test_a_section_runs_through_the_later_answers_of_its_turn_to_the_next_title_of_its_level(mocker, later, expected):
    first = "## Une\n\nTexte.\n"
    messages = turn(first, *later)

    assert shown(excerpt(mocker, messages, 2, name(first, "section"))) == expected


def test_a_section_closed_in_its_answer_does_not_take_the_later_answers(mocker):
    first = "## Une\n\nTexte.\n\n## Deux\n\nAutre.\n"

    assert shown(excerpt(mocker, turn(first, "Suite.\n"), 2, name(first, "section"))) == "Une\nTexte."


def test_a_section_ends_with_its_turn(mocker):
    first = "## Une\n\nTexte.\n"
    messages = [*turn(first), (4, "user", "Autre question"), (5, "assistant", "Autre réponse.\n")]

    assert shown(excerpt(mocker, messages, 2, name(first, "section"))) == "Une\nTexte."


def test_a_section_does_not_take_the_answers_of_a_turn_still_running(mocker):
    first = "## Une\n\nTexte.\n"
    messages = [*turn(first), (4, "user", "Autre question"), (5, "assistant", "En cours.\n")]

    assert shown(excerpt(mocker, messages, 2, name(first, "section"), running=True)) == "Une\nTexte."
