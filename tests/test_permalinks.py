"""Slicing a message into sections, tables and charts, and finding the one a link names."""

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
    ],
    ids=["ligne-en-gras", "titre-de-section", "sans-titre", "titre-mermaid", "gras-au-dessus-du-graphique"],
)
def test_a_figure_is_titled_by_itself_its_caption_or_its_section(text, expected):
    figure = next(a for a in permalinks.anchors(text) if a.kind != "section")

    assert figure.title == expected


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
