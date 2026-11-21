"""Retour et Avance du navigateur : la page que htmx remet en place vit, et suit ce qu'elle montre."""

import re
import uuid
from collections.abc import Callable

import pytest
from playwright.sync_api import Page, Route, expect

pytestmark = pytest.mark.browser

FILLER = "Du texte pour que la réponse dépasse la hauteur de l'écran. " * 120
SECTIONS = f"Plan\n\n## Premier point\n\n{FILLER}\n\n## Second point\n\n{FILLER}"

SENDS = {
    "bouton": lambda page: page.locator("#chatSendBtn").click(),
    "entrée": lambda page: page.locator("#chatInput").press("Enter"),
}


@pytest.fixture
def errors(page: Page) -> list[str]:
    """Les erreurs JavaScript de la page, levées ou écrites dans la console."""
    found: list[str] = []
    page.on("pageerror", lambda error: found.append(str(error)))
    page.on("console", lambda message: message.type == "error" and found.append(message.text))
    return found


def start_conversation(page: Page, visit: Callable[[str], None], ask: Callable[[str], None], question: str) -> str:
    """Une conversation ouverte par la page Nouvelle conversation, son premier tour terminé."""
    visit("/explorations/new")
    ask(question)
    expect(page.locator(".event-final-answer")).to_have_count(1, timeout=15000)
    return re.search(r"/explorations/([0-9a-f-]{36})", page.url).group(1)


def leave_for_conversations(page: Page) -> None:
    """Ouvre la liste des conversations, jusqu'au focus de sa recherche que l'installation de la page donne."""
    page.locator("#nav-primary a[href='/conversations?show=convos']").click()
    expect(page.locator("#rechercherSearchInput")).to_be_focused()


@pytest.mark.parametrize("send", SENDS.values(), ids=SENDS.keys())
def test_back_to_a_saved_conversation_binds_the_page_to_it(
    errors: list[str], conversation: str, visit, ask: Callable[[str], None], page: Page, send
):
    ask(SECTIONS)
    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15000)
    other = start_conversation(page, visit, ask, "Autre conversation")
    visit(f"/explorations/{conversation}")
    expect(page.locator("#tocContent .toc-entry")).to_have_count(2)
    page.locator("#tocContent .toc-entry").evaluate_all("entries => entries.forEach((e) => { e.dataset.left = ''; })")
    page.locator(f"#sidebar-recents a[href='/explorations/{other}']").click()
    expect(page.locator(".event-final-answer")).to_contain_text(["Réponse factice : Autre conversation"])

    page.go_back()

    expect(page).to_have_url(re.compile(rf"/explorations/{conversation}$"))
    expect(page.locator("#tocContent .toc-entry[data-left]")).to_have_count(0)
    expect(page.locator(".event-final-answer")).to_have_count(2)
    expect(page.locator(".event-final-answer").first).to_contain_text("Réponse factice : Première question")

    heading = page.locator(".event-assistant h2", has_text="Premier point")
    expect(heading).not_to_be_in_viewport()
    page.locator("#tocContent .toc-entry", has_text="Premier point").click()
    expect(heading).to_be_in_viewport()

    page.locator("#editTitleBtn").click()
    page.locator("#convTitleInput").fill("Titre après le retour")
    with page.expect_request(lambda r: r.method == "PATCH" and r.url.endswith(f"/api/conversations/{conversation}")):
        page.locator("#saveTitleBtn").click()

    page.locator("#chatInput").fill("Après le retour")
    with page.expect_request(f"**/api/conversations/{conversation}/messages", timeout=5000):
        send(page)
    expect(page.locator(".event-final-answer").last).to_contain_text("Réponse factice : Après le retour", timeout=15000)
    assert errors == []


def test_back_to_a_new_conversation_shows_its_messages(errors: list[str], conversation: str, page: Page):
    leave_for_conversations(page)

    page.go_back()

    expect(page).to_have_url(re.compile(rf"/explorations/{conversation}$"))
    expect(page.locator(".event-final-answer")).to_contain_text("Réponse factice : Première question")
    expect(page.locator("#loadingConversation")).to_have_count(0)
    assert errors == []


def test_back_to_the_conversations_list_keeps_it_usable(errors: list[str], conversation: str, visit, page: Page):
    visit("/conversations?show=convos")
    entry = page.locator(f"#searchResultsList a[href='/explorations/{conversation}']")
    entry.click()
    expect(page.locator(".event-final-answer")).to_contain_text("Réponse factice : Première question")

    page.go_back()

    expect(page).to_have_url(re.compile(r"/conversations\?show=convos$"))
    entry.click()
    expect(page).to_have_url(re.compile(rf"/explorations/{conversation}$"))
    expect(page.locator(".event-final-answer")).to_contain_text("Réponse factice : Première question")
    assert errors == []


def test_forward_after_back_shows_the_conversation_left(
    errors: list[str], conversation: str, visit, ask: Callable[[str], None], page: Page
):
    other = start_conversation(page, visit, ask, SECTIONS)
    visit(f"/explorations/{conversation}")
    expect(page.locator(".event-final-answer")).to_contain_text("Réponse factice : Première question")
    page.locator(f"#sidebar-recents a[href='/explorations/{other}']").click()
    page.locator("#tocContent .toc-entry", has_text="Second point").click()
    expect(page).to_have_url(re.compile(rf"/explorations/{other}#second-point$"))
    page.go_back()
    expect(page.locator(".event-final-answer")).to_contain_text(["Réponse factice : Première question"])

    page.go_forward()

    expect(page).to_have_url(re.compile(rf"/explorations/{other}#second-point$"))
    expect(page.locator(".event-final-answer")).to_contain_text(["Réponse factice : Plan"])
    with page.expect_request(f"**/api/conversations/{other}/messages", timeout=5000):
        ask("Après l'avance")
    expect(page.locator(".event-final-answer").last).to_contain_text("Réponse factice : Après l'avance", timeout=15000)
    assert errors == []


def test_back_onto_a_running_turn_follows_it_to_its_end(
    errors: list[str], conversation: str, ask: Callable[[str], None], page: Page
):
    ask("[slow:4] Réponse lente")
    expect(page.locator(".event-assistant", has_text="Morceau 1.")).to_be_visible()
    leave_for_conversations(page)

    page.go_back()

    expect(page.locator(".event-final-answer").last).to_contain_text("Morceau 4.", timeout=15000)
    expect(page.locator("#chatCancelBtn")).to_be_hidden()
    expect(page.locator("#chatSendBtn")).to_be_enabled()
    assert errors == []


def test_back_to_the_new_conversation_page_starts_one(
    errors: list[str], fake_agent, visit, ask: Callable[[str], None], page: Page
):
    visit("/conversations?show=convos")
    page.locator("#nav-primary a[href='/explorations/new']").click()
    expect(page.locator("#emptyState")).to_be_visible()
    leave_for_conversations(page)

    page.go_back()

    expect(page).to_have_url(re.compile(r"/explorations/new$"))
    ask("Depuis la page remise en place")
    expect(page.locator(".event-final-answer")).to_contain_text(
        "Réponse factice : Depuis la page remise en place", timeout=15000
    )
    assert errors == []


def test_back_to_the_dashboards_page_copies_a_link_once(errors: list[str], visit, page: Page):
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    visit("/dashboards")
    leave_for_conversations(page)

    page.go_back()

    # Why: la page ne montre de bouton de copie qu'à côté d'un TDB publié ; on en pose un pareil.
    page.locator("#section-dashboards").evaluate(
        "(section, html) => section.insertAdjacentHTML('beforeend', html)",
        '<button type="button" id="copyProbe" data-action="copy-url" data-url="/lien">'
        '<i class="ri-file-copy-line"></i></button>',
    )
    icon = page.locator("#copyProbe i")
    page.locator("#copyProbe").click()
    expect(icon).to_have_class("ri-check-line text-success")
    expect(icon).to_have_class("ri-file-copy-line")
    assert page.evaluate("navigator.clipboard.readText()") == "/lien"
    assert errors == []


def test_back_to_a_job_run_polls_that_run_and_only_while_shown(errors: list[str], visit, page: Page):
    run = str(uuid.uuid4())
    summary = {"text": "Avant le départ"}
    polls = []

    def answer(route: Route) -> None:
        polls.append(route.request.url)
        route.fulfill(json={"id": run, "status": "running", "summary": summary["text"]})

    page.route(f"**/api/jobs/runs/{run}", answer)
    page.route(f"**/api/jobs/runs/{run}/events", lambda route: route.fulfill(json=[]))
    visit(f"/jobs/runs/{run}")
    expect(page.locator("#summary")).to_have_text("Avant le départ")
    page.locator("#back-link").click()
    expect(page).to_have_url(re.compile(r"/jobs$"))
    shown = len(polls)
    page.wait_for_timeout(3500)
    assert len(polls) == shown
    summary["text"] = "Après le retour"

    page.go_back()

    expect(page.locator("#summary")).to_have_text("Après le retour")
    assert errors == []
