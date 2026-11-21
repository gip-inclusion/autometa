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

LONG = "Longue\n\n## Méthode\n\n" + "Une ligne de texte.\n\n" * 60 + "Fin."


def answer_to(question: str, ask: Callable[[str], None], page: Page) -> Locator:
    ask(question)
    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    return page.locator(".event-final-answer").last


@pytest.fixture
def answer(conversation: str, ask: Callable[[str], None], page: Page):
    return answer_to(QUESTION, ask, page)


def test_a_finished_answer_offers_a_link_for_itself_each_section_and_each_table(
    answer, conversation: str, base_url: str
):
    expect(answer.locator(".permalink-btn")).to_have_count(4)
    links = answer.locator(".permalink-btn").evaluate_all("buttons => buttons.map((b) => b.dataset.url)")

    shape = rf"{base_url}/explorations/{conversation}/\d+(?:/(\w+-\d+)-[0-9a-f]{{6}})?"
    shapes = [re.fullmatch(shape, link) for link in links]
    assert all(shapes), links
    assert sorted(shape[1] for shape in shapes if shape[1]) == ["section-1", "section-2", "table-1"]


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

    expect(answer.locator(".permalink-btn[data-url*='/chart-1-']")).to_have_count(1)
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
    link = answer.locator(".permalink-btn[data-url*='/table-1-']").get_attribute("data-url")
    opened = re.sub(r"[0-9a-f]{6}$", "000000", link) if stale else link

    visit(opened)

    expect(page.locator(highlighted)).to_have_count(1)
    expect(page.locator(".permalink-target")).to_have_count(1)
    expect(page).to_have_url(opened)


def test_a_link_opens_its_conversation_marked_in_the_sidebar_and_navigable(answer, conversation: str, page: Page):
    link = answer.locator(".permalink-btn[data-url*='/table-1-']").get_attribute("data-url")
    fresh = page.context.new_page()
    recent = fresh.locator(f"#sidebar-recents a[href='/explorations/{conversation}']")

    fresh.goto(link, wait_until="domcontentloaded")

    expect(fresh.locator("table.permalink-target")).to_have_count(1)
    expect(recent).to_have_class(re.compile(r"\bactive\b"))

    fresh.locator("#sidebar a[href='/explorations/new']").click()
    expect(fresh).to_have_url(re.compile(r"/explorations/new$"))
    recent.click()

    expect(fresh).to_have_url(re.compile(rf"/explorations/{conversation}$"))
    expect(fresh.locator(".event-final-answer")).to_have_count(2)
    expect(recent).to_have_class(re.compile(r"\bactive\b"))


def test_the_table_of_contents_outlines_sections_and_figures(answer, conversation: str, page: Page):
    entries = page.locator("#tocContent .toc-entry")

    expect(entries).to_have_text(["Candidatures", "Candidatures", "Méthode"])
    expect(entries.nth(1)).to_have_class(re.compile(r"\btoc-level-3\b"))
    expect(entries.nth(1).locator(".ri-table-line")).to_have_count(1)

    entries.nth(1).dispatch_event("click")

    expect(page).to_have_url(re.compile(rf"/explorations/{conversation}/\d+/table-1-[0-9a-f]{{6}}$"))


def test_a_heading_link_shows_at_rest_and_a_figure_link_only_under_the_pointer_over_its_corner(answer, page: Page):
    table = answer.locator("table")
    figure_link = answer.locator(".permalink-btn[data-url*='/table-1-']")
    expect(figure_link).to_have_count(1)

    page.mouse.move(0, 0)

    expect(answer.locator("h2 .permalink-btn").first).not_to_have_css("opacity", "0")
    expect(figure_link).to_have_css("opacity", "0")

    table.hover()

    expect(figure_link).not_to_have_css("opacity", "0")
    link_box, table_box = figure_link.bounding_box(), table.bounding_box()
    assert table_box["x"] <= link_box["x"] and link_box["x"] + link_box["width"] <= table_box["x"] + table_box["width"]
    assert table_box["y"] <= link_box["y"] < table_box["y"] + table_box["height"] / 2


def test_putting_the_links_again_wraps_each_figure_once(answer, page: Page):
    expect(answer.locator(".permalink-btn")).to_have_count(4)

    page.evaluate("refreshPermalinks()")
    page.evaluate("refreshPermalinks()")

    expect(answer.locator(".permalink-btn")).to_have_count(4)
    expect(answer.locator(".permalink-figure")).to_have_count(1)
    expect(answer.locator(".permalink-figure > table")).to_have_count(1)


def test_a_heading_link_from_before_permalinks_still_lands(conversation: str, ask: Callable[[str], None], page: Page):
    answer_to(LONG, ask, page)
    fresh = page.context.new_page()

    fresh.goto(f"/explorations/{conversation}#methode", wait_until="domcontentloaded")

    expect(fresh.locator("h2#methode")).to_be_in_viewport()


def test_a_link_to_an_answer_not_displayed_opens_the_conversation_at_its_end(
    answer, ask: Callable[[str], None], page: Page
):
    link = answer.locator(".permalink-btn[data-url*='/table-1-']").get_attribute("data-url")
    answer_to(LONG, ask, page)
    fresh = page.context.new_page()
    # Why: la vue minimale masque ainsi les réponses intermédiaires, que l'agent factice ne sait pas produire.
    fresh.add_init_script(
        "addEventListener('DOMContentLoaded', () => document.head.insertAdjacentHTML("
        "'beforeend', '<style>.event-assistant:has(table) { display: none }</style>'))"
    )

    fresh.goto(link, wait_until="domcontentloaded")

    expect(fresh.locator(".event-final-answer").last.get_by_text("Fin.")).to_be_in_viewport()
    expect(fresh.locator(".permalink-target")).to_have_count(0)


def test_the_permalink_request_carries_the_link_and_nothing_else(conversation: str, page: Page):
    fresh = page.context.new_page()

    with fresh.expect_request("**/anchors*") as request:
        fresh.goto(f"/explorations/{conversation}/1/table-1-000000?utm_source=slack", wait_until="domcontentloaded")

    assert request.value.url.endswith(f"/api/conversations/{conversation}/anchors?m=1&a=table-1-000000")


@pytest.mark.parametrize(
    "failure",
    [lambda route: route.abort(), lambda route: route.fulfill(status=200, body="<html>")],
    ids=["réseau", "réponse-illisible"],
)
def test_a_running_conversation_resumes_when_its_permalinks_fail(
    conversation: str, ask: Callable[[str], None], page: Page, failure: Callable
):
    ask("[slow:6] Longue réponse")
    expect(page.locator("#chatCancelBtn")).to_be_visible()
    fresh = page.context.new_page()
    fresh.route("**/anchors*", failure)

    fresh.goto(f"/explorations/{conversation}", wait_until="domcontentloaded")

    expect(fresh.locator(".event-final-answer").last).to_contain_text("Réponse factice : [slow:6]", timeout=15_000)


def test_an_answer_gets_its_links_as_soon_as_a_waiting_message_follows_it(
    conversation: str, ask: Callable[[str], None], page: Page
):
    ask("[slow:2] Chiffres\n\n## Candidatures")
    expect(page.locator("#chatCancelBtn")).to_be_visible()
    queued = page.request.post(
        f"/api/conversations/{conversation}/messages", data={"content": "[slow:8] Suite", "queue": True}
    )
    assert queued.json()["status"] == "queued"

    expect(page.locator("#chatOutput .event-user").last).to_have_text("[slow:8] Suite", timeout=15_000)

    expect(page.locator(".permalink-btn[data-url*='/section-1-']")).to_have_count(1, timeout=4_000)
