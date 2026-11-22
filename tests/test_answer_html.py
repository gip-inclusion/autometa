"""Rendu serveur des réponses et des questions : même HTML que marked et DOMPurify dans la page, liens compris."""

import json
import logging
import re
import time
from html.parser import HTMLParser
from pathlib import Path

import pytest

from lib import answer_html
from lib.answer_html import Link, render_answer, render_user

CASES = json.loads((Path(__file__).parent / "fixtures" / "answer_html_cases.json").read_text())


def canonical(html: str) -> str:
    """Le HTML sans les blancs qu'un navigateur n'affiche pas ; ceux d'un bloc de code comptent."""
    parts = re.split(r"(<pre>.*?</pre>)", html, flags=re.DOTALL)
    return "".join(
        part if part.startswith("<pre>") else re.sub(r"\s*([<>])\s*", r"\1", re.sub(r"\s+", " ", part))
        for part in parts
    )


def elements(html: str) -> list[tuple[str, dict[str, str | None]]]:
    """Chaque balise ouvrante du HTML et ses attributs, lus comme un navigateur les lit."""
    found = []
    reader = HTMLParser()
    reader.handle_starttag = lambda tag, attrs: found.append((tag, dict(attrs)))
    reader.feed(html)
    return found


def link(kind: str, start: int, end: int = 0, level: int = 2) -> Link:
    return Link(
        kind, start, end, level, f'data-anchor="{kind}-{start}"', f'<button data-for="{kind}-{start}"></button>'
    )


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_an_answer_renders_as_the_page_renders_it(case):
    expected = case.get("server_html", case["page_html"])

    assert canonical(render_answer(case["input"])) == canonical(expected), case["pins"]


def test_the_known_differences_with_the_page_are_the_listed_ones():
    assert sorted(case["name"] for case in CASES if "server_html" in case) == [
        "emph3_strong_closer_glued_to_em_closer",
        "list2_item_then_quote",
        "list2_item_then_table",
        "list2_star_space_line",
        "policy_checkbox_raw",
    ]


@pytest.mark.parametrize(
    "text",
    [
        '<a title="a <input b" href="https://exemple.fr">t</a> " onmouseover="alert(1)" x="',
        '<a title="<span class=&quot;mb0&quot;></span>">t</a>',
        '<input type="checkbox" title="a>b" onclick="alert(1)">',
        '<div class="permalink-figure"><button class="permalink-btn" data-url="javascript:alert(1)">x</button></div>',
        '<h2 data-anchor="1-section-1" class="me0">Titre</h2>',
    ],
    ids=["chevron-dans-un-attribut", "marque-devinée", "case-tapée", "lien-imité", "ancre-imitée"],
)
def test_text_cannot_write_what_only_the_application_adds(text):
    found = elements(render_answer(text))

    assert not [tag for tag, _ in found if tag in ("input", "button")]
    assert not [name for _, attrs in found for name in attrs if name == "class" or name.startswith(("on", "data-"))]


def test_each_render_marks_what_it_adds_with_a_class_of_its_own(mocker):
    cleaned = mocker.spy(answer_html.nh3, "clean")

    rendered = [render_answer("- [x] fait") for _ in range(2)]

    marks = [re.search(r'<span class="(m[0-9a-f]{32})c1"></span>', call.args[0])[1] for call in cleaned.call_args_list]
    assert len(set(marks)) == 2
    assert rendered == ['<ul>\n<li><input checked="" disabled="" type="checkbox"> fait</li>\n</ul>\n'] * 2


def test_rendering_writes_none_of_the_parser_s_debug_lines(caplog):
    caplog.set_level(logging.DEBUG)

    render_answer("# Titre\n\n- un\n- deux\n\n| a | b |\n|---|---|\n| 1 | 2 |")

    assert [record.name for record in caplog.records] == []


LINKED = "Intro\n\n## Titre **gras**\n\n| a | b |\n|---|---|\n| 1 | 2 |\n```mermaid\npie\n```\n"


def test_each_link_is_written_on_its_element_with_its_button():
    rendered = render_answer(LINKED, (link("section", 2), link("table", 4, 7), link("chart", 7)))

    assert canonical(rendered) == canonical(
        "<p>Intro</p>"
        '<h2 data-anchor="section-2">Titre <strong>gras</strong><button data-for="section-2"></button></h2>'
        '<div class="permalink-figure"><table data-anchor="table-4">'
        "<thead><tr><th>a</th><th>b</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr></tbody></table>"
        '<button data-for="table-4"></button></div>'
        '<div class="permalink-figure"><pre data-anchor="chart-7"><code class="language-mermaid">pie\n</code></pre>'
        '<button data-for="chart-7"></button></div>'
    )


@pytest.mark.parametrize(
    ("text", "placed"),
    [
        ("texte\n\n## Titre", link("section", 0)),
        ("## Titre", link("section", 0, level=3)),
        ("Titre\n-----", link("section", 0)),
        ("<details>\n## Titre\n</details>", link("section", 1)),
        ("```\n## Titre\n```", link("section", 1)),
        ("| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |", link("table", 0, 3)),
        ("<details>\n| a | b |\n|---|---|\n| 1 | 2 |\n</details>", link("table", 1, 4)),
        ("```python\npie\n```", link("chart", 0)),
        ("texte\n```mermaid\npie\n```", link("chart", 2)),
    ],
    ids=[
        "autre-ligne",
        "autre-niveau",
        "titre-souligné",
        "titre-dans-du-html",
        "titre-dans-du-code",
        "tableau-plus-long",
        "tableau-dans-du-html",
        "code-d-un-autre-langage",
        "graphique-à-une-autre-ligne",
    ],
)
def test_an_element_the_slicer_and_the_renderer_read_differently_gets_no_link(text, placed):
    assert render_answer(text, (placed,)) == render_answer(text)


def test_a_link_reaches_an_element_nested_in_a_list_and_leaves_its_neighbours():
    text = "- point\n\n  | a | b |\n  |---|---|\n  | 1 | 2 |\n\n| c | d |\n|---|---|\n| 3 | 4 |"

    rendered = render_answer(text, (link("table", 2, 5),))

    assert rendered.count('<div class="permalink-figure"><table data-anchor="table-2">') == 1
    assert rendered.count("<table") == 2 and rendered.count("<button") == 1


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("<b>gras</b> et **gras**", "<p>&lt;b&gt;gras&lt;/b&gt; et <strong>gras</strong></p>\n"),
        ("<div>\nbloc\n</div>", "&lt;div&gt;\nbloc\n&lt;/div&gt;"),
        ("![nom](https://exemple.fr/i.png)", "<p>nom</p>\n"),
        (
            '[doc](https://exemple.fr/a?b=1&c=2 "Titre")',
            '<p><a href="https://exemple.fr/a?b=1&amp;c=2" target="_blank" rel="noopener noreferrer nofollow ugc" '
            'title="Titre">doc</a></p>\n',
        ),
        (
            "voir https://exemple.fr/page.",
            '<p>voir <a href="https://exemple.fr/page" target="_blank" rel="noopener noreferrer nofollow ugc">'
            "https://exemple.fr/page</a>.</p>\n",
        ),
        ("[lien](javascript:alert(1))", "<p>lien</p>\n"),
        ("[lien](data:text/html,x)", "<p>lien</p>\n"),
        ("[lien](java\tscript:alert(1))", "<p>[lien](java\tscript:alert(1))</p>\n"),
        ("[ancre](#section) [page](/c/new)", None),
        ("- [x] fait\n- [ ] à faire", None),
        ('- <input class="task-list-item-checkbox" checked="checked"> tapé', None),
        ("", ""),
    ],
    ids=[
        "html-en-ligne",
        "bloc-html",
        "image",
        "lien-titré",
        "adresse-nue",
        "javascript",
        "data",
        "caractère-de-contrôle",
        "liens-locaux",
        "cases",
        "case-tapée",
        "vide",
    ],
)
def test_a_question_shows_its_markdown_its_html_as_text_and_only_safe_links(text, expected):
    rendered = render_user(text)

    if expected is not None:
        assert rendered == expected
    assert not re.search(r"<(?!/?(?:p|a|strong|ul|li|input)\b)", rendered)
    assert rendered.count("<input") == text.count("- [")
    assert rendered.count("<a ") == rendered.count('target="_blank" rel="noopener noreferrer nofollow ugc"')
    assert "javascript:" not in rendered.replace("](javascript:", "").replace("](java\tscript:", "")


@pytest.mark.parametrize(
    ("text", "kept"),
    [
        ('<a href=" data:text/html,x">a</a>', {}),
        ('<a href="da\tta:text/html,x">a</a>', {}),
        ('<a href="&#1;data:text/html,x">a</a>', {}),
        ('<area href="&Tab;data:text/html,x">', {}),
        ('<video poster=" data:image/png;base64,AA"></video>', {}),
        ('<img src=" data:image/png;base64,AA">', {}),
        ('<img src="data:image/png;base64,AA">', {"src": "data:image/png;base64,AA"}),
        ('<div background="javascript:alert(1)">x</div>', {}),
        ('<q cite=" JaVa\nScript:alert(1)">x</q>', {}),
        ('<img srcset="javascript:alert(1) 1x">', {}),
        ('<span title="javascript:texte" lang="fr">x</span>', {"title": "javascript:texte", "lang": "fr"}),
        ('<time datetime="12:30">x</time>', {"datetime": "12:30"}),
        ('<a href="/c/abcd2345#titre">x</a>', {"href": "/c/abcd2345#titre"}),
        ('<a href="mailto:contact@exemple.fr">x</a>', {"href": "mailto:contact@exemple.fr"}),
    ],
    ids=[
        "data-après-une-espace",
        "data-coupé-d-une-tabulation",
        "data-après-un-caractère-de-contrôle",
        "data-après-une-entité",
        "data-sur-une-affiche",
        "image-data-après-une-espace",
        "image-data",
        "javascript-sur-un-fond",
        "javascript-sur-une-citation",
        "javascript-dans-un-jeu-d-images",
        "titre-libre",
        "heure",
        "adresse-locale",
        "courriel",
    ],
)
def test_an_attribute_keeps_its_value_only_if_dompurify_would_read_it_as_safe(text, kept):
    assert elements(render_answer(text))[-1][1] == kept


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("- [X] fait", '<ul>\n<li><input checked="" disabled="" type="checkbox"> fait</li>\n</ul>\n'),
        ("1. [ ] à faire", '<ol>\n<li><input disabled="" type="checkbox"> à faire</li>\n</ol>\n'),
        ("- \\[x] échappé", "<ul>\n<li>[x] échappé</li>\n</ul>\n"),
        ("- [x]sans espace", "<ul>\n<li>[x]sans espace</li>\n</ul>\n"),
        ("- [x] \nsuite", '<ul>\n<li><input checked="" disabled="" type="checkbox"><br>suite</li>\n</ul>\n'),
        ("[x] hors liste", "<p>[x] hors liste</p>\n"),
        (
            "[x]: https://exemple.fr\n\n- [x] fait",
            '<ul>\n<li><input checked="" disabled="" type="checkbox"> fait</li>\n</ul>\n',
        ),
    ],
    ids=["majuscule", "liste-numérotée", "crochet-échappé", "sans-espace", "fin-de-ligne", "hors-liste", "référence-x"],
)
def test_a_list_item_opening_with_a_box_is_a_task(text, expected):
    assert render_answer(text) == expected


@pytest.mark.parametrize(
    ("text", "linked"),
    [
        ("https://exemple.fr/a.", "https://exemple.fr/a"),
        ("https://exemple.fr/a?!.,:;*_'\"~)", "https://exemple.fr/a"),
        ("https://exemple.fr/a(b)", "https://exemple.fr/a(b)"),
        ("https://exemple.fr/a(b))).", "https://exemple.fr/a(b)"),
        ("https://exemple.fr/a(b", "https://exemple.fr/a"),
        ("https://exemple.fr/a&amp;", "https://exemple.fr/a"),
        ("https://exemple.fr/a&x;&amp;", "https://exemple.fr/a"),
        ("https://exemple.fr/a&amp;b", "https://exemple.fr/a&b"),
        ("https://exemple.fr/a;", "https://exemple.fr/a"),
        ("https://exemple.fr/a(b https://exemple.fr/c)", "https://exemple.fr/a"),
        ("https://exemple.fr/a&b;c&amp;", "https://exemple.fr/a&b;c"),
        ("https://exemple.fr/a&amp; suite;", "https://exemple.fr/a"),
    ],
    ids=[
        "point",
        "ponctuation-en-série",
        "parenthèses-fermées",
        "parenthèses-en-trop",
        "parenthèse-ouverte",
        "entité-finale",
        "entités-en-chaîne",
        "entité-au-milieu",
        "point-virgule",
        "parenthèse-fermée-plus-loin",
        "entité-seulement-en-fin",
        "entité-avant-une-espace",
    ],
)
def test_a_bare_address_ends_where_marked_ends_it(text, linked):
    assert elements(render_answer(text))[1] == ("a", {"href": linked})


N = 100_000
HOSTILE = {
    "adresse-puis-ponctuation": "http://a" + "~*_'\"" * (N // 5),
    "adresses-collées": "www." * (N // 4),
    "adresses-à-parenthèse-ouverte": "www.a(" * (N // 6),
    "adresses-à-parenthèse-ouverte-entre-crochets": "[www.a(" * (N // 7),
    "adresses-à-requête-ouverte": "http://a.b/c?d=(" * (N // 16),
    "adresses-puis-long-mot": "www.a(" * (N // 12) + "a" * (N // 2) + ";",
    "adresses-à-entité": "www.a&amp;" * (N // 10),
    "tirets": "a-" * (N // 2),
    "plus": "+" * N + "x",
    "soulignés": "a_" * (N // 2),
    "plus-et-soulignés": "a+a_" * (N // 4),
    "arobase-après-des-points": "a." * (N // 2) + "@",
    "esperluettes": "&" * N,
    "tilde-dans-une-emphase": "*a ~b* c~ " * (N // 10),
    "emphases-ouvertes-puis-tildes": "*a " * (N // 6) + "~b " * (N // 6),
    "barrés-emboîtés": "*a ~b~ " * (N // 7),
    "tildes-échappés": "\\~" * (N // 2),
    "étoiles-et-soulignés": "*a _b " * (N // 6),
    "cases": "- [x] a\n" * (N // 8),
    "titres-et-tableaux": "## h\n\n|a|\n|-|\n|b|\n\n" * (N // 18),
}


@pytest.mark.parametrize("render", [render_answer, render_user], ids=["réponse", "question"])
@pytest.mark.parametrize("text", HOSTILE.values(), ids=HOSTILE.keys())
def test_rendering_stays_linear_on_hostile_text(render, text):
    started = time.perf_counter()

    render(text)

    # Why: lu en moins d'une seconde ici ; ces formes prenaient de 30 secondes à plusieurs minutes, sur l'unique worker.
    assert time.perf_counter() - started < 5
