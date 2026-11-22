"""Une conversation telle que le serveur la rend : blocs, liens, rapports, renvois, et le tour en cours suivi par un flux."""

import json
import re
import time

import pytest

from lib import permalinks
from web import conversation_html
from web.conversation_html import Live, answer_block, file_blocks, file_size, output, progress, thread, user_html

CONV = "abcd2345"
TABLE = "| a | b |\n|---|---|\n| 1 | 2 |\n"


def blocks(conv_id: str, messages: list[tuple[int, str, str]], **given) -> list[dict]:
    return thread(conv_id, messages, **given)["blocks"]


def shape(found: list[dict]) -> list[tuple]:
    return [(b["kind"], b["ids"], bool(b.get("report")), bool(b.get("final"))) for b in found]


def anchors(html: str) -> list[str]:
    return re.findall(r'data-anchor="([^"]+)"', html)


def test_consecutive_agent_messages_make_one_block_until_a_tool_call_or_a_question():
    messages = [
        (1, "user", "Question"),
        (2, "assistant", "Début "),
        (3, "system", "{}"),
        (4, "assistant", "suite"),
        (5, "tool_use", ""),
        (6, "tool_result", ""),
        (7, "assistant", "Fin"),
        (8, "user", "Autre"),
        (9, "assistant", "Réponse"),
    ]

    found = blocks(CONV, messages)

    assert shape(found) == [
        ("user", [1], False, False),
        ("assistant", [2, 4], False, False),
        ("assistant", [7], False, True),
        ("user", [8], False, False),
        ("assistant", [9], False, True),
    ]
    assert "<p>Début suite</p>" in found[1]["html"]


def test_messages_joined_in_a_block_are_read_as_one_text():
    found = blocks(CONV, [(1, "assistant", "| a | b |\n"), (2, "assistant", "|---|---|\n| 1 | 2 |\n")])

    assert "<table>" in found[0]["html"]
    assert anchors(found[0]["html"]) == []


@pytest.mark.parametrize(
    ("messages", "expected"),
    [
        (
            [(1, "assistant", f"## A\n\n{TABLE}"), (2, "assistant", "## B\n")],
            ["1-section-1", "1-table-1", "2-section-1"],
        ),
        ([(1, "assistant", "Texte sans fin de ligne"), (2, "assistant", "## B\n\n## C\n")], ["2-section-2"]),
        ([(1, "assistant", ""), (2, "assistant", "## B\n")], ["2-section-1"]),
        ([(1, "assistant", "## A\r\n\r\n## B\r\n")], ["1-section-1", "1-section-2"]),
        ([(1, "assistant", "## A\r## B\n\n## C\n")], []),
        ([(1, "assistant", "> ## Cité\n\n<details>\n## Brut\n</details>\n\n## Vu\n")], ["1-section-2"]),
    ],
    ids=["deux-messages", "collé-à-une-ligne", "message-vide", "fins-windows", "retour-chariot-seul", "désaccords"],
)
def test_each_element_is_linked_under_its_own_message_or_not_at_all(messages, expected):
    assert anchors(blocks(CONV, messages)[0]["html"]) == expected


def test_a_link_carries_the_address_and_digest_of_the_slicer_its_title_and_its_level():
    text = f"## Chiffres *clés*\n\n{TABLE}"
    section, table = permalinks.anchors(text)

    html = blocks(CONV, [(7, "assistant", text)])[0]["html"]

    assert html.startswith(
        f'<button type="button" class="permalink-btn" data-url="/c/{CONV}/7" title="Copier le lien vers cette réponse"'
    )
    assert (
        f'<h2 data-anchor="7-section-1" data-anchor-kind="section" data-anchor-title="Chiffres clés" '
        f'data-anchor-level="2" data-anchor-url="/c/{CONV}/7/section-1-{section.digest}">'
    ) in html
    assert (
        f'<table data-anchor="7-table-1" data-anchor-kind="table" data-anchor-title="Chiffres clés" '
        f'data-anchor-level="3" data-anchor-url="/c/{CONV}/7/table-1-{table.digest}">'
    ) in html
    assert f'data-url="/c/{CONV}/7/table-1-{table.digest}" title="Copier le lien vers ce tableau"' in html


def test_a_title_cannot_leave_its_attribute():
    html = blocks(CONV, [(1, "assistant", '## "><img src=x onerror=alert(1)>\n')])[0]["html"]

    assert 'data-anchor-title="&#34;&gt;&lt;img src=x onerror=alert(1)&gt;"' in html
    assert html.count("onerror") == 1


REPORT = "---\nquery category: Trafic <b>\ndate: 2026-01-05\nwebsite: emplois\nvide:  \n---\n## Résumé\n\nVoir 2026-01-trafic.md\n"


def test_an_answer_opening_with_front_matter_is_a_report_its_header_apart_from_its_body():
    block = blocks(CONV, [(1, "user", "Rapport ?"), (2, "assistant", REPORT)])[1]

    assert (block["report"], block.get("final")) == (True, None)
    assert block["html"].count("permalink-btn") == 1
    assert (
        '<div class="report-header"><div class="report-title"><i class="ri-file-text-line"></i> Trafic &lt;b&gt;</div>'
        '<div class="report-meta"><i class="ri-calendar-line"></i> 2026-01-05</div>'
        '<div class="report-meta"><i class="ri-global-line"></i> emplois</div>'
        '<a href="/api/reports/2026-01-trafic.md" target="_blank" class="report-link">'
        '<i class="ri-external-link-line"></i> Voir le rapport complet</a></div>'
        '<div class="report-body"><h2 data-anchor="2-section-1"'
    ) in block["html"]
    assert "query category" not in block["html"]


def test_a_report_without_fields_is_titled_rapport_and_the_last_plain_answer_before_it_stays_final():
    found = blocks(CONV, [(1, "assistant", "Réponse"), (2, "tool_use", ""), (3, "assistant", "---\n\n---\nCorps")])

    assert shape(found) == [("assistant", [1], False, True), ("assistant", [3], True, False)]
    assert '<div class="report-title"><i class="ri-file-text-line"></i> Rapport</div></div>' in found[1]["html"]


@pytest.mark.parametrize(
    ("front_matter", "title"),
    [
        ("query category: Trafic\nquery category:  ", "Rapport"),
        ("query category:\r Trafic", "Trafic"),
        ("query category: Tra\rfic", "Rapport"),
        ("query category: Trafic\r", "Rapport"),
        ("catégorie: Trafic\nquery category Trafic", "Rapport"),
        ("query category: a: b", "a: b"),
    ],
    ids=[
        "valeur-vide-en-dernier",
        "retour-avant-la-valeur",
        "retour-dans-la-valeur",
        "retour-final",
        "pas-un-champ",
        "deux-points",
    ],
)
def test_a_report_field_is_read_as_the_page_reads_it(front_matter, title):
    html = answer_block(CONV, [(1, f"---\n{front_matter}\n---\nCorps")], False)["html"]

    assert f'<div class="report-title"><i class="ri-file-text-line"></i> {title}</div>' in html


@pytest.mark.parametrize(
    ("text", "linked"),
    [
        ("voir 2026-01-trafic.md et 2026-02-autre.md", "2026-01-trafic.md"),
        ("x2026-01-a_b-c.md", "2026-01-a_b-c.md"),
        ("2026-01-.md puis 12026-02-ok.md", "2026-02-ok.md"),
        ("2026-01-trafic.txt, 2026-1-a.md, 2026-01-trafic .md", None),
    ],
    ids=["premier-nom", "au-milieu-d-un-mot", "nom-vide-écarté", "aucun"],
)
def test_a_report_links_the_first_report_file_its_text_names(text, linked):
    html = answer_block(CONV, [(1, f"---\n\n---\n{text}")], False)["html"]

    assert re.findall(r'href="/api/reports/([^"]+)"', html) == [linked] * bool(linked)


@pytest.mark.parametrize(
    ("content", "address", "title"),
    [
        ('{"report_id": 12, "title": "Bilan <2026>"}', "/rapports/12", "Bilan &lt;2026&gt;"),
        ('{"id": 7}', "/rapports/7", "Rapport"),
        ('{"report_id": "12", "id": true}', "/rapports/0", "Rapport"),
        ("pas du json", "/rapports/0", "Rapport"),
        ("[1, 2]", "/rapports/0", "Rapport"),
    ],
    ids=["rapport", "ancien-champ", "identifiants-non-numériques", "illisible", "pas-un-objet"],
)
def test_a_saved_report_shows_as_a_card(content, address, title):
    card = blocks(CONV, [(1, "report", content)])[0]

    assert (card["kind"], card["ids"]) == ("report", [1])
    assert f'<a href="{address}" class="report-card-link">' in card["html"]
    assert f'<span class="report-card-title">{title}</span>' in card["html"]


def test_a_limit_notice_shows_its_text_escaped():
    notice = blocks(CONV, [(1, "limit", "Limite <atteinte>")])[0]

    assert (notice["kind"], notice["html"]) == (
        "limit",
        '<i class="ri-time-line" aria-hidden="true"></i><div>Limite &lt;atteinte&gt;</div>',
    )


FILE = "[Uploaded file: {name}]\n- Size: {size} bytes\n- Type: {mime}\n- Path: /tmp/x\n"


@pytest.mark.parametrize(
    ("mime", "icon"),
    [
        ("image/svg+xml", "ri-image-line"),
        ("text/csv", "ri-file-text-line"),
        ("application/json", "ri-file-text-line"),
        ("application/pdf", "ri-file-pdf-line"),
        ("application/vnd.ms-excel", "ri-file-excel-line"),
        ("application/msword", "ri-file-word-line"),
        ("application/zip", "ri-file-line"),
    ],
)
def test_an_attached_file_shows_as_a_pill_with_the_icon_of_its_type(mime, icon):
    html = user_html(FILE.format(name="données <1>.bin", size="1,280", mime=mime) + "\n---\n\nVoici **le** fichier")

    assert html == (
        f'<div class="file-context-pills"><span class="file-context-pill" title="{mime}"><i class="{icon}"></i> '
        'données &lt;1&gt;.bin <span class="file-context-size">(1.3 Ko)</span></span></div>'
        '<div class="user-text"><p>Voici <strong>le</strong> fichier</p>\n</div>'
    )


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (
            "[Uploaded file: a.txt]\n- Path: /tmp/a\n```\ncontenu\n```\n[Uploaded file: b.txt]\n- Path: /tmp/b\n",
            '<div class="file-context-pills"><span class="file-context-pill" title=""><i class="ri-file-line"></i> a.txt'
            '</span><span class="file-context-pill" title=""><i class="ri-file-line"></i> b.txt</span></div>',
        ),
        ("Sans fichier <i>", '<div class="user-text"><p>Sans fichier &lt;i&gt;</p>\n</div>'),
        ("", '<div class="user-text"></div>'),
    ],
    ids=["fichiers-seuls", "texte-seul", "vide"],
)
def test_a_question_shows_its_files_then_its_text(content, expected):
    assert user_html(content) == expected


@pytest.mark.parametrize(
    ("content", "names"),
    [
        ("[Uploaded file: a]\n- x\n[Uploaded file: b]\n- y\n", ["a", "b"]),
        ("[Uploaded file: [Uploaded file: a]\n- x\n", ["[Uploaded file: a"]),
        ("[Uploaded file: ]\n- x\n[Uploaded file: b]\n- y\n", ["b"]),
        ("[Uploaded file: a] \n- x\n[Uploaded file: b]\n- y\n", ["b"]),
        ("[Uploaded file: a]\n- x\n```\n[Uploaded file: b]\n- y\n```\n", ["a"]),
        ("[Uploaded file: a]\nsans propriété\n", []),
    ],
    ids=["deux-fichiers", "ouverture-répétée", "nom-vide", "nom-mal-fermé", "bloc-dans-un-contenu", "sans-propriété"],
)
def test_file_blocks_are_found_where_the_page_finds_them(content, names):
    assert [name for _, _, name in file_blocks(content)] == names


def test_a_question_past_the_queue_s_limit_is_shown_as_typed():
    text = "**gras** <b>x</b>\nligne " + "a" * 20_000

    html = user_html(FILE.format(name="a.txt", size="12", mime="text/plain") + "\n---\n\n" + text)

    assert html.count('class="file-context-pill"') == 1
    assert f'<div class="user-text">**gras** &lt;b&gt;x&lt;/b&gt;<br>ligne {"a" * 20_000}</div>' in html


def test_a_question_at_the_queue_s_limit_is_still_read_as_markdown():
    assert "<strong>gras</strong>" in user_html("**gras** " + "a" * 19_991)


N = 200_000
HOSTILE = {
    "champ-d-espaces": lambda: answer_block(CONV, [(1, "---\na:" + " " * N + "\r\n---\nx")], False),
    "champ-de-deux-points": lambda: answer_block(CONV, [(1, "---\n" + "a:" * (N // 2) + "\r\n---\nx")], False),
    "dates-sans-fichier": lambda: answer_block(CONV, [(1, "---\n\n---\n" + "0000-00-" * (N // 8))], False),
    "fichiers-jamais-nommés": lambda: user_html("[Uploaded file: " * (N // 16)),
    "fichiers-nommés-à-la-fin": lambda: user_html("[Uploaded file: " * (N // 16) + "]"),
    "longue-question": lambda: user_html("http://a" + "~*_'\"" * (N // 5)),
}


@pytest.mark.parametrize("render", HOSTILE.values(), ids=HOSTILE.keys())
def test_a_block_stays_fast_on_hostile_text(render):
    started = time.perf_counter()

    render()

    assert time.perf_counter() - started < 5


@pytest.mark.parametrize(
    ("size", "expected"),
    [(0, "0 o"), (1023, "1023 o"), (1024, "1.0 Ko"), (1280, "1.3 Ko"), (1536, "1.5 Ko"), (5 * 1024**2, "5.0 Mo")],
)
def test_a_file_size_reads_as_the_composer_writes_it(size, expected):
    assert file_size(size) == expected


def test_a_block_cut_by_the_message_asked_after_is_given_whole():
    messages = [
        (1, "user", "Question"),
        (2, "assistant", "Réponse. "),
        (3, "system", "{}"),
        (4, "assistant", "*Interrompu.*"),
    ]

    found = blocks(CONV, messages, after=2)

    assert shape(found) == [("assistant", [2, 4], False, True)]
    assert "<p>Réponse. <em>Interrompu.</em></p>" in found[0]["html"]
    assert blocks(CONV, messages, after=4) == []


def test_a_block_the_renderer_cannot_read_shows_its_text_and_leaves_the_others(mocker, caplog):
    broken = mocker.patch.object(
        conversation_html, "render_user", side_effect=[RecursionError("trop profond"), "<p>ok</p>"]
    )

    found = blocks(CONV, [(1, "user", "<b>illisible</b>"), (2, "assistant", "Réponse"), (3, "user", "lisible")])

    assert broken.call_count == 2
    assert shape(found) == [("user", [1], False, False), ("assistant", [2], False, True), ("user", [3], False, False)]
    assert found[0]["html"] == "<pre>&lt;b&gt;illisible&lt;/b&gt;</pre>"
    assert "Block 1 of conversation abcd2345 could not be rendered" in caplog.text


U, A, CALL, RESULT = "user", "assistant", "tool_use", "tool_result"


def references(found: list[dict]) -> list[list[str]]:
    """Under each answer, the index of each tool call it refers to."""
    return [re.findall(r'data-action-index="(\d+)"', "".join(b["references"])) for b in found if b["kind"] == A]


@pytest.mark.parametrize(
    ("kinds", "expected"),
    [
        ([U, A, CALL, RESULT, CALL, RESULT, A], [["1", "2"], []]),
        ([U, CALL, RESULT, CALL, RESULT, A], [["1", "2"]]),
        ([U, CALL, RESULT, A, CALL, RESULT, A], [["2"], []]),
        ([U, CALL, RESULT, A, U, A], [["1"], []]),
        ([U, A, CALL, CALL, RESULT, RESULT, U, CALL, RESULT, A], [["1", "2"], ["3"]]),
        ([U, A, RESULT, CALL], [[]]),
        ([U, A, "system", A, CALL, RESULT], [["1"]]),
        ([U, CALL, RESULT], []),
        ([U, A, CALL, U, RESULT, CALL, RESULT, A], [[], ["1"]]),
    ],
    ids=[
        "appels-après-une-réponse",
        "appels-avant-la-seule-réponse",
        "appels-avant-et-après",
        "appels-avant-puis-tour-suivant",
        "appels-parallèles-et-deux-tours",
        "résultat-sans-appel",
        "réponse-en-deux-messages",
        "aucune-réponse",
        "appel-laissé-sans-résultat-par-le-tour-d-avant",
    ],
)
def test_an_answer_refers_to_the_tool_calls_made_after_it_or_before_the_first_of_its_turn(kinds, expected):
    shown = thread(CONV, [(n, kind, "texte") for n, kind in enumerate(kinds, 1)])

    assert references(shown["blocks"]) == expected
    assert [pill["index"] for pill in shown["pills"]] == list(range(1, len(shown["pills"]) + 1))


def test_a_reference_names_its_pill_by_index_label_and_icon():
    call = json.dumps({"tool": "Read", "category": "Read: other", "input": {"file_path": '/tmp/"notes".md'}})

    shown = thread(CONV, [(1, U, "Question"), (2, A, "Réponse"), (3, CALL, call), (4, RESULT, "")], actions_before=4)

    assert shown["blocks"][1]["references"] == [
        '<span class="action-footnote" data-action-index="5" title="&#34;notes&#34;.md">'
        '<i class="ri-file-text-line"></i></span>'
    ]
    assert [(pill["index"], pill["message"]) for pill in shown["pills"]] == [(5, 4)]


def test_only_the_pills_of_results_after_the_message_asked_after_are_given():
    messages = [(n, kind, "texte") for n, kind in enumerate([U, CALL, RESULT, A, CALL, RESULT], 1)]

    shown = thread(CONV, messages, after=4)

    assert [(pill["index"], pill["message"]) for pill in shown["pills"]] == [(2, 6)]
    assert shown["blocks"] == []


RUNNING = [(1, U, "Question"), (2, A, "## Début\n\n"), (3, CALL, "{}"), (4, RESULT, ""), (5, A, f"## Suite\n\n{TABLE}")]


def test_the_answer_a_running_turn_ends_on_is_partial_without_links_and_not_yet_final():
    first, last = blocks(CONV, RUNNING, question=1)[1:]

    assert (first["partial"], last["partial"], last.get("final")) == (False, True, None)
    assert anchors(first["html"]) == ["2-section-1"] and "permalink-btn" in first["html"]
    assert anchors(last["html"]) == [] and "permalink-btn" not in last["html"]
    assert "<h2>Suite</h2>" in last["html"] and "<table>" in last["html"]


@pytest.mark.parametrize(
    ("messages", "question"),
    [(RUNNING, None), ([*RUNNING, (6, CALL, "{}")], 1), ([*RUNNING, (6, U, "Autre")], 6)],
    ids=["tour-fini", "appel-d-outil-ensuite", "question-suivante"],
)
def test_an_answer_no_longer_growing_is_whole(messages, question):
    last = blocks(CONV, messages, question=question)[2]

    assert last["partial"] is False
    assert anchors(last["html"]) == ["5-section-1", "5-table-1"]
    assert bool(last.get("final")) is (messages[-1][1] != CALL)


@pytest.mark.parametrize(
    ("messages", "expected"),
    [
        ([(1, U, "Question")], ""),
        ([(1, U, "Question"), (2, A, "Texte")], "Appel modèle · génération de la réponse"),
        ([(1, U, "Q"), (2, A, "Texte"), (3, CALL, '{"tool": "Bash"}'), (4, RESULT, "")], "Outil · Bash"),
        (
            [
                (1, U, "Q"),
                (2, "system", '{"subtype": "api_retry", "attempt": 2, "max_retries": 5, "error_status": 529}'),
            ],
            "Appel API · tentative 2/5 · dernier statut 529 · erreur",
        ),
        (
            [(1, U, "Q"), (2, "system", '{"subtype": "api_retry", "error": "surcharge"}')],
            "Appel API · tentative ?/? · surcharge",
        ),
        ([(1, A, "Avant"), (2, U, "Question"), (3, "system", '{"subtype": "init"}')], ""),
    ],
    ids=["rien-encore", "réponse", "outil", "nouvel-essai", "essai-sans-détail", "tour-d-avant-ignoré"],
)
def test_progress_says_what_the_agent_is_doing_from_its_last_telling_message(messages, expected):
    assert progress(messages) == expected


def live(mocker, messages: list, after: int) -> Live:
    """A stream's view of a conversation whose messages are this list, which the test grows in place."""
    mocker.patch.object(
        conversation_html.store, "get_message_kinds", side_effect=lambda conv: [(n, kind) for n, kind, _ in messages]
    )
    mocker.patch.object(
        conversation_html.store,
        "get_thread_messages",
        side_effect=lambda conv, since: [message for message in messages if message[0] >= since],
    )
    return Live(CONV, after)


def looked(shown: dict | None) -> tuple | None:
    return shown and (
        [(b["ids"], b["partial"]) for b in shown["blocks"]],
        [pill["index"] for pill in shown["pills"]],
        shown["settled"],
    )


def test_a_stream_gives_at_each_look_the_blocks_from_the_first_that_changed_and_the_new_pills(mocker):
    messages = [(1, U, "Avant"), (2, CALL, "{}"), (3, RESULT, ""), (4, A, "Réponse"), (5, U, "Question")]
    stream = live(mocker, messages, 4)

    assert looked(stream.look(True)) == ([([5], False)], [], 4)
    assert stream.look(True) is None
    messages += [(6, A, "Dé")]
    assert looked(stream.look(True)) == ([([6], True)], [], 4)
    messages[-1] = (6, A, "Début")
    assert looked(stream.look(True)) == ([([6], True)], [], 4)
    messages += [(7, CALL, '{"tool": "Bash"}')]
    assert looked(stream.look(True)) == ([([6], False)], [], 4)
    messages += [(8, CALL, '{"tool": "Read"}')]
    said = stream.look(True)
    assert (looked(said), said["status"]) == (([], [], 4), "Outil · Read")
    assert stream.look(True) is None
    messages += [(9, RESULT, ""), (10, A, "Fin")]
    assert looked(stream.look(True)) == ([([6], False), ([10], True)], [2], 4)
    last = stream.look(False)
    assert looked(last) == ([([10], False)], [], 10)
    assert (last["blocks"][0]["final"], last["running"], last["status"]) == (True, False, "")
    assert stream.look(False) is None


def test_a_stream_renders_again_only_the_block_that_changed(mocker):
    messages = [(1, U, "Question"), (2, A, "Première"), (3, CALL, "{}"), (4, RESULT, ""), (5, A, "Seconde")]
    stream = live(mocker, messages, 0)
    rendered = mocker.spy(conversation_html, "block")

    stream.look(True)
    messages[-1] = (5, A, "Seconde, plus longue")
    stream.look(True)

    assert [call.args[2] for call in rendered.call_args_list] == [
        [(1, "Question")],
        [(2, "Première")],
        [(5, "Seconde")],
        [(5, "Seconde, plus longue")],
    ]


@pytest.mark.parametrize(
    ("after", "expected"),
    [
        (0, ([([1], False), ([2], False), ([5], False), ([6], False)], [1], 6)),
        (4, ([([5], False), ([6], False)], [], 6)),
        (2, ([([5], False), ([6], False)], [1], 6)),
        (6, ([], [], 6)),
        (9, ([], [], 9)),
    ],
    ids=["tout", "dernier-tour", "milieu-d-un-tour", "à-jour", "au-delà"],
)
def test_a_stream_first_brings_what_the_page_lacks_even_when_that_is_nothing(mocker, after, expected):
    messages = [(1, U, "Une"), (2, A, "Réponse"), (3, CALL, "{}"), (4, RESULT, ""), (5, U, "Deux"), (6, A, "Fin")]

    assert looked(live(mocker, messages, after).look(False)) == expected


def test_a_stream_numbers_its_pills_after_those_of_the_turns_before(mocker):
    messages = [(n, kind, "{}") for n, kind in enumerate([U, CALL, RESULT, CALL, U, CALL, RESULT, RESULT, U, A], 1)]
    stream = live(mocker, messages, 8)
    messages += [(11, CALL, "{}"), (12, RESULT, "")]

    shown = stream.look(True)

    assert [(pill["index"], pill["message"]) for pill in shown["pills"]] == [(3, 12)]
    assert references(shown["blocks"]) == [["3"]]


MESSAGES = [
    (10, "user", "Première"),
    (11, "assistant", "Réponse une"),
    (12, "tool_result", ""),
    (20, "user", "Seconde"),
    (21, "assistant", "Réponse en cours"),
]


@pytest.mark.parametrize(
    ("messages", "running", "expected"),
    [
        (MESSAGES, False, ([[10], [11], [20], [21]], 21)),
        (MESSAGES, True, ([[10], [11]], 19)),
        (MESSAGES[:3], False, ([[10], [11]], 12)),
        (MESSAGES[:1], True, ([], 9)),
        ([], True, ([], 0)),
        ([], False, ([], 0)),
    ],
    ids=["terminée", "tour-en-cours", "finit-par-un-outil", "premier-tour-en-cours", "en-cours-sans-question", "vide"],
)
def test_the_output_holds_the_finished_turns_and_the_message_the_stream_resumes_after(
    mocker, messages, running, expected
):
    read = mocker.patch.object(conversation_html.store, "get_thread_messages", return_value=messages)

    found = output(CONV, running)

    assert ([b["ids"] for b in found["blocks"]], found["last_id"]) == expected
    assert found["pills"] == []
    read.assert_called_once_with(CONV)


@pytest.mark.parametrize(
    ("text", "buttons"),
    [
        ("## Seule\n\nTexte.\n", ["cette réponse"]),
        ("## Seule\n\nTexte.\n\n### Dessous\n\nTexte.\n", ["cette réponse", "cette section"]),
        ("## Une\n\nTexte.\n\n## Deux\n\nTexte.\n", ["cette réponse", "cette section", "cette section"]),
        ("Intro.\n\n## Après\n\nTexte.\n", ["cette réponse", "cette section"]),
    ],
)
def test_a_section_that_is_the_whole_answer_has_no_link_button_of_its_own(text, buttons):
    html = conversation_html.answer_block(CONV, [(7, text)], False)["html"]

    assert re.findall(r'title="Copier le lien vers ([^"]+)"', html) == buttons
    assert html.count('data-anchor-kind="section"') == len(re.findall(r"^#+ ", text, re.M))
