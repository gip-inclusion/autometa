"""Preuves navigateur — la page d'une conversation arrive dessinée par le serveur, sans attendre ses messages."""

import re
from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser

FIGURES = "Chiffres\n\n## Candidatures\n\n| Mois | Total |\n|---|---|\n| Janvier | 12 |\n\n## Méthode\n\nTexte."
RICH = "[tools:1] Bilan\n\n## Plan\n\n- [x] fait\n- [ ] à faire\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n```options\nOui\nNon\n```"
BLOCKS = "blocks => blocks.map((block) => block.outerHTML)"


def hold_the_api(page: Page) -> None:
    """Laisse sans réponse ce que la page demande sur ses conversations : messages et rendu des tours."""
    page.route(re.compile(r"/api/conversations/[^/]+(/blocks.*)?$"), lambda route: None)


@pytest.fixture
def figures(conversation: str, ask: Callable[[str], None], page: Page) -> str:
    """Une conversation dont le second tour porte deux sections et un tableau."""
    ask(FIGURES)
    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    return conversation


def test_the_page_of_a_conversation_is_served_with_its_finished_turns_drawn(figures: str, page: Page):
    served = page.request.get(f"/c/{figures}").text()

    for drawn in (
        'class="event-block event-user"',
        "Réponse factice : Première question",
        "event-final-answer",
        "<h2 data-anchor=",
        '<div class="permalink-figure"><table data-anchor=',
        f'data-url="/c/{figures}/',
    ):
        assert drawn in served
    assert "loadingConversation" not in served


def test_a_conversation_shows_its_answers_and_its_link_s_target_before_any_of_its_messages_is_fetched(
    figures: str, page: Page
):
    link = page.locator(".permalink-btn[data-url*='/table-1-']").get_attribute("data-url")
    fresh = page.context.new_page()
    hold_the_api(fresh)

    fresh.goto(link, wait_until="domcontentloaded")

    expect(fresh.locator(".event-final-answer")).to_have_count(2)
    expect(fresh.locator("table.permalink-target")).to_be_in_viewport()
    expect(fresh.locator("#tocContent .toc-entry")).to_have_text(["Candidatures", "Candidatures", "Méthode"])
    expect(fresh).to_have_url(link)


def test_the_sidebar_back_and_forward_show_a_conversation_without_waiting_for_its_messages(
    figures: str, visit: Callable[[str], None], page: Page
):
    other = page.request.post("/api/conversations").json()["id"]
    hold_the_api(page)
    visit(f"/c/{other}")
    page.evaluate("window.sameDocument = true")
    answers = page.locator(".event-final-answer")

    page.locator(f"#sidebar-recents a[href='/c/{figures}']").click()

    expect(answers).to_have_count(2)
    expect(answers.last.locator(".permalink-figure > table")).to_be_visible()
    expect(page.locator("#loadingConversation, #chatOutput .spinner")).to_have_count(0)

    page.go_back()
    expect(page).to_have_url(re.compile(rf"/c/{other}$"))
    expect(answers).to_have_count(0)
    page.go_forward()

    expect(answers).to_have_count(2)
    expect(page.locator("#tocContent .toc-entry")).to_have_count(3)
    page.locator(f"#sidebar-recents a[href='/c/{other}']").click()
    expect(answers).to_have_count(0)
    page.go_back()

    expect(answers).to_have_count(2)
    expect(page.locator("#loadingConversation, #chatOutput .spinner")).to_have_count(0)
    assert page.evaluate("window.sameDocument") is True


def test_the_end_of_a_turn_leaves_the_blocks_a_reload_gives(conversation: str, ask: Callable[[str], None], page: Page):
    blocks = page.locator("#chatOutput > *")
    ask(RICH)
    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    expect(page.locator("#chatOutput > [data-live]")).to_have_count(0)
    expect(page.locator(".action-footnote")).to_have_count(1)
    expect(page.locator(".options-buttons button")).to_have_count(2)
    handed_over = blocks.evaluate_all(BLOCKS)

    page.reload(wait_until="domcontentloaded")

    expect(page.locator(".action-footnote")).to_have_count(1)
    assert blocks.evaluate_all(BLOCKS) == handed_over
    page.locator(".options-buttons button", has_text="Non").click()
    expect(page.locator("#chatInput")).to_have_value("Non")
