"""Retour et Avance du navigateur : la page que htmx remet en place vit, et suit ce qu'elle montre."""

import re
import shutil
import uuid
from collections.abc import Callable, Iterator

import pytest
from playwright.sync_api import Page, Route, expect
from sqlalchemy import delete

from lib.dashboards import create_dashboard
from web import config, s3
from web.db import get_db
from web.models import Dashboard

pytestmark = pytest.mark.browser

FILLER = "Du texte pour que la réponse dépasse la hauteur de l'écran. " * 120
SECTIONS = f"Plan\n\n## Premier point\n\n{FILLER}\n\n## Second point\n\n{FILLER}"

SENDS = {
    "bouton": lambda page: page.locator("#chatSendBtn").click(),
    "entrée": lambda page: page.locator("#chatInput").press("Enter"),
}

# Why: les commandes du moteur factice sont trop courtes pour que leur action montre le bouton qui ouvre la modale.
DIALOGS = {
    "modale": (
        {"width": 1280, "height": 720},
        lambda page: page.evaluate("openActionModal('Commande', 'echo 0', true)"),
        "#actionDetailModal",
        "#actionDetailModal .btn-close",
    ),
    "volet": (
        {"width": 375, "height": 667},
        lambda page: page.locator(".action-footnote").click(),
        "#actionsOffcanvas",
        "#actionsOffcanvas .btn-close",
    ),
    "signalement": (
        {"width": 1280, "height": 720},
        lambda page: page.locator("#chatFlagBtn").click(),
        "#flagDialog",
        "#flagCancel",
    ),
}


@pytest.fixture
def errors(page: Page) -> list[str]:
    """Les erreurs JavaScript de la page, levées ou écrites dans la console."""
    found: list[str] = []
    page.on("pageerror", lambda error: found.append(str(error)))
    page.on("console", lambda message: message.type == "error" and found.append(message.text))
    return found


@pytest.fixture
def favourites(page: Page) -> Iterator[list[str]]:
    """Deux conversations en favori sur l'accueil, retirées des favoris à la fin."""
    conversations = [page.request.post("/api/conversations").json()["id"] for _ in range(2)]
    for conversation in conversations:
        assert page.request.post(f"/api/favorites/conversation/{conversation}").ok
    yield conversations
    for conversation in conversations:
        page.request.delete(f"/api/favorites/conversation/{conversation}")


@pytest.fixture
def dashboard() -> Iterator[str]:
    """Un TDB à cron, créé par la bibliothèque de l'application, retiré à la fin."""
    slug = f"e2e-history-{uuid.uuid4().hex[:8]}"
    create_dashboard(
        slug=slug,
        title="Parcours historique",
        description="e2e",
        website=None,
        category=None,
        tags=[],
        has_cron=True,
        first_author_email="e2e@inclusion.gouv.fr",
        created_in_conversation_id=None,
    )
    yield slug
    with get_db() as session:
        session.execute(delete(Dashboard).where(Dashboard.slug == slug))
    shutil.rmtree(config.INTERACTIVE_DIR / slug, ignore_errors=True)
    for entry in s3.interactive.list_files(f"{slug}/"):
        s3.interactive.delete(entry["path"])


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


@pytest.mark.parametrize("shown", DIALOGS.values(), ids=DIALOGS.keys())
def test_back_and_forward_with_a_dialog_open_leave_both_pages_usable(
    errors: list[str], conversation: str, visit, ask: Callable[[str], None], page: Page, shown
):
    viewport, open_dialog, dialog, close = shown
    ask("[tools:1] Une action")
    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15000)
    visit("/conversations?show=convos")
    entry = page.locator(f"#searchResultsList a[href='/explorations/{conversation}']")
    entry.click()
    expect(page.locator(".event-final-answer")).to_have_count(2)
    page.set_viewport_size(viewport)
    open_dialog(page)
    # Why: Bootstrap ignore la fermeture d'une modale qui s'ouvre encore ; ouverte, elle a pris le focus.
    expect(page.locator(f"{dialog}:focus-within")).to_be_visible()

    page.go_back()

    expect(page).to_have_url(re.compile(r"/conversations\?show=convos$"))
    expect(page.locator(".modal-backdrop, .offcanvas-backdrop")).to_have_count(0)
    expect(page.locator("body")).not_to_have_class(re.compile(r"\bmodal-open\b"))
    expect(page.locator("body")).not_to_have_css("overflow", "hidden")
    entry.click(trial=True)

    page.go_forward()

    expect(page.locator(".event-final-answer")).to_have_count(2)
    expect(page.locator(dialog)).to_be_hidden()
    open_dialog(page)
    expect(page.locator(dialog)).to_be_visible()
    page.locator(close).click()
    expect(page.locator(dialog)).to_be_hidden()
    expect(page.locator(".modal-backdrop, .offcanvas-backdrop")).to_have_count(0)
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


def test_back_to_a_dashboard_settings_page_keeps_its_buttons(errors: list[str], dashboard: str, visit, page: Page):
    visit(f"/dashboards/{dashboard}/edit")
    leave_for_conversations(page)

    page.go_back()

    page.locator("[data-action='edit-title']").click()
    expect(page.locator("#titleInput")).to_be_visible()
    page.locator("[data-action='cron-history']").click()
    expect(page.locator("#cronLogModal")).to_contain_text("Aucun historique")
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


def test_back_to_the_home_page_keeps_its_favourites_draggable(
    errors: list[str], favourites: list[str], visit, page: Page
):
    visit("/")
    leave_for_conversations(page)

    page.go_back()

    tiles = page.locator("#favoritesGrid .accueil-favorite")
    with page.expect_request(lambda r: r.method == "PATCH" and r.url.endswith("/api/favorites/order"), timeout=5000):
        tiles.nth(0).drag_to(tiles.nth(1))
    assert errors == []


def test_the_page_copies_kept_by_htmx_2_0_4_are_removed(visit, page: Page):
    visit("/")
    page.evaluate("localStorage.setItem('htmx-history-cache', '[]')")

    page.reload(wait_until="domcontentloaded")

    assert page.evaluate("localStorage.getItem('htmx-history-cache')") is None
