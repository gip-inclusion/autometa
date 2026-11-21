"""Preuves navigateur — lien vers une réponse, une section, un tableau, et mise en évidence à l'ouverture."""

import re
from collections.abc import Callable

import pytest
from playwright.sync_api import Locator, Page, expect

pytestmark = pytest.mark.browser

QUESTION = "Chiffres\n\n## Candidatures\n\n| Mois | Total |\n|---|---|\n| Janvier | 12 |\n\n## Méthode\n\nTexte."

# Why: le serveur voit un titre dans le bloc HTML, la page un titre dans la citation — autant de titres de part et
# d'autre, pas les mêmes.
DISAGREEMENT = (
    "Désaccord\n\n## Contexte\n\n> ## Note importante\n> texte\n\n"
    "<details>\n## Détail des calculs\n</details>\n\n## Résultats"
)

# Why: le titre du serveur garde l'échappement « \# » ; le sommaire montre la section telle que la page l'affiche.
CHART = 'Graphique\n\n## Statuts \\#1\n\n```mermaid\npie title Par statut\n    "Acceptées" : 3\n    "Refusées" : 1\n```'


def answer_to(question: str, ask: Callable[[str], None], page: Page) -> Locator:
    ask(question)
    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    return page.locator(".event-final-answer").last


@pytest.fixture
def answer(conversation: str, ask: Callable[[str], None], page: Page):
    return answer_to(QUESTION, ask, page)


def test_a_finished_answer_offers_a_link_for_itself_each_section_and_each_table(answer, conversation: str):
    expect(answer.locator(".permalink-btn")).to_have_count(4)
    links = answer.locator(".permalink-btn").evaluate_all("buttons => buttons.map((b) => b.dataset.url)")

    assert all(f"/explorations/{conversation}?m=" in link for link in links)
    assert sorted(re.sub(r"-[0-9a-f]{6}$", "", link.split("&a=")[1]) for link in links if "&a=" in link) == [
        "section-1",
        "section-2",
        "table-1",
    ]


def test_an_answer_the_page_reads_otherwise_than_the_server_keeps_its_own_link_only(
    conversation: str, ask: Callable[[str], None], page: Page
):
    answer = answer_to(DISAGREEMENT, ask, page)

    expect(answer.locator(".permalink-btn")).to_have_count(1)
    expect(answer.locator("h2")).to_have_text(["Contexte", "Note importante", "Résultats"])
    expect(page.locator("#tocContent .toc-entry")).to_have_text(["Contexte", "Note importante", "Résultats"])
    expect(page.locator("#tocContent .toc-entry.toc-level-1")).to_have_count(3)


def test_a_chart_gets_its_link_and_its_entry_in_the_table_of_contents(
    conversation: str, ask: Callable[[str], None], page: Page
):
    answer = answer_to(CHART, ask, page)

    expect(answer.locator(".permalink-btn[data-url*='a=chart-1-']")).to_have_count(1)
    expect(page.locator("#tocContent .toc-entry")).to_have_text(["Statuts #1", "Par statut"])
    expect(page.locator("#tocContent .toc-entry").nth(1).locator(".ri-bar-chart-2-line")).to_have_count(1)


@pytest.mark.parametrize(
    ("stale", "highlighted"),
    [(False, "table.permalink-target"), (True, ".event-assistant.permalink-target")],
    ids=["tableau", "empreinte-périmée"],
)
def test_opening_a_link_highlights_its_target_or_the_whole_answer(
    answer, visit: Callable[[str], None], page: Page, stale: bool, highlighted: str
):
    link = answer.locator(".permalink-btn[data-url*='a=table-1-']").get_attribute("data-url")

    visit(re.sub(r"[0-9a-f]{6}$", "000000", link) if stale else link)

    expect(page.locator(highlighted)).to_have_count(1)
    expect(page.locator(".permalink-target")).to_have_count(1)
    assert "a=table-1-" in page.url


def test_the_table_of_contents_outlines_sections_and_figures(answer, page: Page):
    entries = page.locator("#tocContent .toc-entry")

    expect(entries).to_have_text(["Candidatures", "Candidatures", "Méthode"])
    expect(entries.nth(1)).to_have_class(re.compile(r"\btoc-level-3\b"))
    expect(entries.nth(1).locator(".ri-table-line")).to_have_count(1)

    entries.nth(1).dispatch_event("click")

    expect(page).to_have_url(re.compile(r"a=table-1-[0-9a-f]{6}$"))


def test_a_heading_link_from_before_permalinks_still_lands(
    answer, conversation: str, visit: Callable[[str], None], page: Page
):
    visit(f"/explorations/{conversation}#methode")

    expect(page.locator("h2#methode")).to_have_text("Méthode")
    expect(page.locator("#tocContent .toc-entry")).to_have_count(3)
