"""Slicing a message into sections, tables and charts, and finding the one a link names."""

import time

import pytest

from lib import permalinks

MESSAGE = """Intro.

## Candidatures

| Mois | Total |
|---|---|
| Janvier | 12 |

### Détail

```mermaid
xychart-beta
    title "Par mois"
```

## Méthode

```python
# pas un titre
| pas | un tableau |
|---|---|
```
"""


def table(name: str) -> str:
    return f"| {name} | Total |\n|---|---|\n| x | 1 |"


def test_anchors_lists_sections_tables_and_charts_in_reading_order():
    found = permalinks.anchors(MESSAGE)

    assert [(a.kind, a.rank) for a in found] == [
        ("section", 1),
        ("table", 1),
        ("section", 2),
        ("chart", 1),
        ("section", 3),
    ]


def test_anchor_texts_are_the_element_itself():
    by_name = {(a.kind, a.rank): a.text for a in permalinks.anchors(MESSAGE)}

    assert by_name["table", 1] == "| Mois | Total |\n|---|---|\n| Janvier | 12 |"
    assert by_name["chart", 1] == 'xychart-beta\n    title "Par mois"'
    assert by_name["section", 2].startswith("### Détail")
    assert "## Méthode" not in by_name["section", 1]
    assert by_name["section", 3].startswith("## Méthode")


def test_anchors_carry_a_title_and_an_outline_level():
    by_name = {(a.kind, a.rank): (a.title, a.level) for a in permalinks.anchors(MESSAGE)}

    assert by_name == {
        ("section", 1): ("Candidatures", 2),
        ("table", 1): ("Candidatures", 3),
        ("section", 2): ("Détail", 3),
        ("chart", 1): ("Par mois", 4),
        ("section", 3): ("Méthode", 2),
    }


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (f"**Candidatures 2026**\n\n{table('A')}", "Candidatures 2026"),
        (f"## Section\n\nUn paragraphe.\n\n{table('A')}", "Section"),
        (table("A"), ""),
        ("```mermaid\n---\ntitle: Flux\n---\nflowchart LR\n```", "Flux"),
        ("**Répartition**\n\n```mermaid\nflowchart LR\n```", "Répartition"),
        ('```mermaid\npie title Répartition\n    "A" : 1\n```', "Répartition"),
        (f"**Total `2026`** :\n{table('A')}", "Total 2026"),
        (f"## **Résultats**\n\n{table('A')}", "Résultats"),
        ("| a | b |\n|---|---|\ntitle | x", ""),
    ],
    ids=[
        "ligne-en-gras",
        "titre-de-section",
        "sans-titre",
        "titre-mermaid",
        "gras-au-dessus-du-graphique",
        "camembert-sur-une-ligne",
        "gras-avec-code",
        "section-en-gras",
        "ligne-title-dans-un-tableau",
    ],
)
def test_a_figure_is_titled_by_itself_its_caption_or_its_section(text, expected):
    figure = next(a for a in permalinks.anchors(text) if a.kind != "section")

    assert figure.title == expected


@pytest.mark.parametrize(
    ("heading", "expected"),
    [
        ("## Langage C#", "Langage C#"),
        ("## Résultats ##", "Résultats"),
        ("## **Résultats** `2026`", "Résultats 2026"),
        ("## Voir [la note](https://example.com/n-1) _complète_", "Voir la note complète"),
        ("## nom_de_colonne", "nom_de_colonne"),
    ],
    ids=["dièse-final", "dièses-de-fermeture", "gras-et-code", "lien-et-italique", "tiret-bas-dans-un-mot"],
)
def test_a_section_is_titled_by_its_heading_as_plain_text(heading, expected):
    assert [a.title for a in permalinks.anchors(heading)] == [expected]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("## Résultats [détaillés](https://example.com/a-1) en 2026", ["Résultatsdétaillésen2026"]),
        ("## " + "mot " * 20, ["mot" * 13 + "m"]),
        ("| a | b \\| c |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |", ["2x2"]),
        ("a | b | c\n---|---|---", ["3x0"]),
        ('```mermaid\npie title Répartition\n    "A" : 1\n```', ["pietitleRépartitionA1"]),
        (
            "Désaccord\n\n## Contexte\n\n> ## Note importante\n> texte\n\n"
            "<details>\n## Détail des calculs\n</details>\n\n## Résultats",
            ["Contexte", "Détaildescalculs", "Résultats"],
        ),
    ],
    ids=["section", "section-longue", "tableau", "tableau-sans-ligne", "graphique", "citation-et-html"],
)
def test_each_anchor_carries_a_witness_the_page_checks_it_against(text, expected):
    assert [a.witness for a in permalinks.anchors(text)] == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("```x``` :\n\n## A\n\n```\n# B\n```\n", ["A"]),
        ("```\n    ```\n## A\n```\n", []),
        ("````\n```\n## A\n````\n", []),
        ("```\n``` x\n## A\n```\n", []),
        ("~~~\n```\n## A\n~~~\n", []),
        ("```\n   `````  \n## A\n", ["A"]),
    ],
    ids=[
        "code-en-ligne",
        "fermeture-trop-indentée",
        "fermeture-trop-courte",
        "texte-après-la-fermeture",
        "autre-caractère",
        "fermeture-valide",
    ],
)
def test_code_fences_open_and_close_as_in_commonmark(text, expected):
    assert [a.title for a in permalinks.anchors(text) if a.kind == "section"] == expected


@pytest.mark.parametrize(
    "text",
    ["a | b\n|" + "-" * 200_000 + "x", "```mermaid\nflowchart\n" + " \n" * 20_000 + "x\n```", "# a\n" * 20_000],
    ids=["séparateur-de-tableau", "graphique-presque-vide", "titres-en-masse"],
)
def test_slicing_stays_fast_on_hostile_text(text):
    started = time.perf_counter()

    permalinks.anchors(text)

    assert time.perf_counter() - started < 1


@pytest.mark.parametrize(
    "text",
    ["Du texte sans rien.", "", "a | b sans ligne de séparation", "```\n## dans un bloc\n```"],
    ids=["texte", "vide", "barre-seule", "bloc-de-code"],
)
def test_anchors_finds_nothing_in_plain_text(text):
    assert permalinks.anchors(text) == []


def test_digest_follows_the_text_not_the_position():
    alone = permalinks.anchors(table("A"))[0]
    moved = permalinks.anchors(f"{table('B')}\n\n{table('A')}")[1]

    assert (alone.rank, moved.rank) == (1, 2)
    assert alone.digest == moved.digest
    assert len(alone.digest) == 6


@pytest.mark.parametrize(
    ("kind", "rank", "digest_of", "expected_rank"),
    [
        ("table", 2, "A", 2),
        ("table", 1, "A", 2),
        ("table", 1, None, None),
        ("section", 2, "A", None),
    ],
    ids=["même-rang", "rang-décalé", "empreinte-inconnue", "autre-genre"],
)
def test_resolve_trusts_the_digest_over_the_rank(kind, rank, digest_of, expected_rank):
    found = permalinks.anchors(f"{table('B')}\n\n{table('A')}")
    digest = permalinks.anchors(table(digest_of))[0].digest if digest_of else "000000"

    hit = permalinks.resolve(found, kind, rank, digest)

    assert (hit and hit.rank) == expected_rank
