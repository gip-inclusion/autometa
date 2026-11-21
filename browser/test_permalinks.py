"""Preuves navigateur — lien vers une réponse, une section, un tableau, et mise en évidence à l'ouverture."""

import re
from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser

QUESTION = "Chiffres\n\n## Candidatures\n\n| Mois | Total |\n|---|---|\n| Janvier | 12 |\n\n## Méthode\n\nTexte."


@pytest.fixture
def answer(conversation: str, ask: Callable[[str], None], page: Page):
    ask(QUESTION)
    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    return page.locator(".event-final-answer").last


def test_a_finished_answer_offers_a_link_for_itself_each_section_and_each_table(answer, conversation: str):
    expect(answer.locator(".permalink-btn")).to_have_count(4)
    links = answer.locator(".permalink-btn").evaluate_all("buttons => buttons.map((b) => b.dataset.url)")

    assert all(f"/explorations/{conversation}?m=" in link for link in links)
    assert sorted(re.sub(r"-[0-9a-f]{6}$", "", link.split("&a=")[1]) for link in links if "&a=" in link) == [
        "section-1",
        "section-2",
        "table-1",
    ]


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
