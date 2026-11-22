"""Rendu serveur des réponses et des questions : même HTML que marked et DOMPurify dans la page, liens compris."""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from lib.answer_html import Link, render_answer, render_user

CASES = json.loads((Path(__file__).parent / "fixtures" / "answer_html_cases.json").read_text())


def canonical(html: str) -> str:
    """Le HTML sans les blancs qu'un navigateur n'affiche pas ; ceux d'un bloc de code comptent."""
    parts = re.split(r"(<pre>.*?</pre>)", html, flags=re.DOTALL)
    return "".join(
        part if part.startswith("<pre>") else re.sub(r"\s*([<>])\s*", r"\1", re.sub(r"\s+", " ", part))
        for part in parts
    )


def elements(html: str) -> list[tuple[str, list[str]]]:
    """Chaque balise ouvrante du HTML et les noms de ses attributs, lus comme un navigateur les lit."""
    found = []
    reader = HTMLParser()
    reader.handle_starttag = lambda tag, attrs: found.append((tag, [name for name, _ in attrs]))
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
    assert not [name for _, names in found for name in names if name == "class" or name.startswith(("on", "data-"))]


def test_the_mark_of_a_render_is_not_the_mark_of_the_next():
    first = render_answer("- [x] fait")

    assert (
        render_answer("- [x] fait")
        == first
        == '<ul>\n<li><input checked="" disabled="" type="checkbox"> fait</li>\n</ul>\n'
    )


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
