"""Preuves navigateur — les conversations à l'adresse /c/ : anciennes adresses, conversations d'avant les identifiants
courts, et aucun lien de l'application vers /explorations."""

import re
import uuid
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import Locator, Page, expect

from web.db import get_db
from web.models import Conversation

pytestmark = pytest.mark.browser

TABLE = "Chiffres\n\n## Candidatures\n\n| Mois | Total |\n|---|---|\n| Janvier | 12 |"
NOTE = {"name": "note.txt", "mimeType": "text/plain", "buffer": b"contenu de la note"}
SPINNING = re.compile(r"\bri-spin\b")

# Why: le lien d'une carte de rapport ou d'application de la liste passe par onclick, pas par href.
ADDRESSES = """() => [...document.querySelectorAll('[href], [hx-get], [hx-push-url], [data-url], [onclick]')].flatMap(
  (el) => [
    el.getAttribute('href'),
    el.getAttribute('hx-get'),
    el.getAttribute('hx-push-url'),
    el.dataset.url,
    el.getAttribute('onclick')?.match(/location\\.href\\s*=\\s*'([^']+)'/)?.[1],
  ].filter(Boolean),
)"""


@pytest.fixture
def old_conversation(fake_agent, page: Page) -> Iterator[str]:
    """Une conversation d'avant les identifiants courts, sous un UUID, insérée en base au nom du navigateur."""
    probe = page.request.post("/api/conversations").json()["id"]
    owner = page.request.get(f"/api/conversations/{probe}").json()["user_id"]
    page.request.delete(f"/api/conversations/{probe}")
    conv_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with get_db() as session:
        session.add(Conversation(id=conv_id, user_id=owner, title="D'avant", created_at=now, updated_at=now))
    yield conv_id
    page.request.post(f"/api/conversations/{conv_id}/cancel")
    page.request.delete(f"/api/conversations/{conv_id}")


def table_permalink(answer: Locator) -> str:
    """L'adresse que copie le lien du tableau d'une réponse."""
    return urlsplit(answer.locator(".permalink-btn[data-url*='/table-1-']").get_attribute("data-url")).path


def test_a_new_conversation_keeps_its_short_address_through_a_whole_journey(
    fake_agent, visit: Callable[[str], None], ask: Callable[[str], None], page: Page
):
    visit("/c/new")
    ask("Première question")
    expect(page.locator(".event-final-answer")).to_contain_text("Réponse factice : Première question", timeout=15_000)
    expect(page).to_have_url(re.compile(r"/c/[0-9a-z]{8}$"))
    conversation = urlsplit(page.url).path.split("/")[2]

    page.reload(wait_until="domcontentloaded")
    expect(page.locator(".event-final-answer")).to_have_count(1)
    page.locator("#chatFileInput").set_input_files(files=[NOTE])
    ask(TABLE)
    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    expect(page.locator(".event-user .file-context-pill")).to_contain_text("note.txt")
    expect(page).to_have_url(re.compile(rf"/c/{conversation}$"))
    expect(page.locator(".event-final-answer").last.locator(".permalink-btn[data-url*='/table-1-']")).to_have_count(1)
    permalink = table_permalink(page.locator(".event-final-answer").last)

    page.locator("#forkConvBtn").click()
    expect(page).to_have_url(re.compile(rf"/c/(?!{conversation})[0-9a-z]{{8}}$"))
    copy = urlsplit(page.url).path.split("/")[2]
    expect(page.locator(".event-final-answer")).to_have_count(2)
    ask("Question dans la copie")
    expect(page.locator(".event-final-answer")).to_have_count(3, timeout=15_000)

    page.locator(f"#sidebar-recents a[href='/c/{conversation}']").click()
    expect(page).to_have_url(re.compile(rf"/c/{conversation}$"))
    expect(page.locator(".event-final-answer")).to_have_count(2)
    page.go_back()
    expect(page).to_have_url(re.compile(rf"/c/{copy}$"))
    expect(page.locator(".event-final-answer")).to_have_count(3)

    fresh = page.context.new_page()
    fresh.goto(permalink, wait_until="domcontentloaded")

    expect(fresh.locator("table.permalink-target")).to_have_count(1)
    expect(fresh).to_have_url(re.compile(rf"{re.escape(permalink)}$"))


def test_a_conversation_with_a_uuid_opens_at_its_old_address_plays_a_turn_and_opens_its_permalinks(
    old_conversation: str, visit: Callable[[str], None], ask: Callable[[str], None], page: Page
):
    visit(f"/explorations/{old_conversation}")
    expect(page).to_have_url(re.compile(rf"/c/{old_conversation}$"))

    ask(TABLE)
    answer = page.locator(".event-final-answer")
    expect(answer).to_contain_text("Réponse factice : Chiffres", timeout=15_000)
    expect(answer.locator(".permalink-btn[data-url*='/table-1-']")).to_have_count(1)
    expect(page).to_have_url(re.compile(rf"/c/{old_conversation}$"))
    permalink = table_permalink(answer)
    fresh = page.context.new_page()

    fresh.goto(permalink.replace("/c/", "/explorations/", 1), wait_until="domcontentloaded")

    expect(fresh).to_have_url(re.compile(rf"{re.escape(permalink)}$"))
    expect(fresh.locator("table.permalink-target")).to_have_count(1)


def test_an_old_permalink_opens_its_element_at_the_new_address(
    conversation: str, ask: Callable[[str], None], page: Page
):
    ask(TABLE)
    answer = page.locator(".event-final-answer").last
    expect(answer.locator(".permalink-btn[data-url*='/table-1-']")).to_have_count(1)
    permalink = table_permalink(answer)
    fresh = page.context.new_page()

    fresh.goto(permalink.replace("/c/", "/explorations/", 1), wait_until="domcontentloaded")

    expect(fresh.locator("table.permalink-target")).to_have_count(1)
    expect(fresh).to_have_url(re.compile(rf"{re.escape(permalink)}$"))


def test_the_old_new_conversation_address_keeps_its_prefilled_question(visit: Callable[[str], None], page: Page):
    visit("/explorations/new?prefill=Cr%C3%A9e%20un%20tableau%20de%20bord%20qui%20")

    expect(page.locator("#chatInput")).to_have_value("Crée un tableau de bord qui ")
    expect(page).to_have_url(re.compile(r"/c/new$"))


def test_no_page_links_a_conversation_at_its_old_address_and_each_link_opens_its_conversation(
    conversation: str, ask: Callable[[str], None], visit: Callable[[str], None], page: Page
):
    ask(TABLE)
    expect(page.locator(".event-final-answer").last.locator(".permalink-btn[data-url*='/table-1-']")).to_have_count(1)
    found = page.evaluate(ADDRESSES)
    visit("/conversations?show=reports")
    reports = page.locator("#main a[href^='/rapports/']")
    pages = ["/", "/conversations?show=convos", "/conversations?show=reports", "/dashboards"]
    pages += [reports.first.get_attribute("href")] if reports.count() else []
    for path in pages:
        visit(path)
        found += page.evaluate(ADDRESSES)

    assert [address for address in found if "/explorations" in address] == []
    paths = {urlsplit(address).path for address in found}
    assert {f"/c/{conversation}", "/c/new"} <= paths
    for path in sorted(p for p in paths if p.startswith("/c/")):
        opened = page.request.get(path)
        assert opened.ok, path
        expected = 'id="chatInput"' if path == "/c/new" else f"loadConversation('{path.split('/')[2]}')"
        assert expected in opened.text(), path


def sidebar_icon(page: Page, conversation: str) -> Locator:
    """L'icône du lien d'une conversation dans les récentes de la barre latérale."""
    return page.locator(f"#sidebar-recents a[href='/c/{conversation}'] i")


def test_the_sidebar_link_of_a_conversation_spins_while_its_turn_runs(
    conversation: str, ask: Callable[[str], None], page: Page
):
    ask("[slow:3] Question lente")

    expect(sidebar_icon(page, conversation)).to_have_class(SPINNING)
    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    expect(sidebar_icon(page, conversation)).not_to_have_class(SPINNING)


def test_the_spinner_of_a_conversation_left_running_goes_once_its_turn_ends(
    conversation: str, ask: Callable[[str], None], visit: Callable[[str], None], page: Page
):
    ask("[slow:4] Question lente")
    expect(page.locator("#chatOutput")).to_contain_text("Morceau 1.", timeout=15_000)
    other = page.request.post("/api/conversations").json()["id"]

    visit(f"/c/{other}")

    expect(sidebar_icon(page, conversation)).to_have_class(SPINNING)
    expect(sidebar_icon(page, conversation)).not_to_have_class(SPINNING, timeout=20_000)
    page.request.delete(f"/api/conversations/{other}")
