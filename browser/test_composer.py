"""Preuves navigateur — état de la barre de saisie : tour en cours, téléversement, double envoi, navigation."""

import re
from collections.abc import Callable

import pytest
from playwright.sync_api import Page, Playwright, Route, expect

pytestmark = pytest.mark.browser

NOTE = {"name": "note.txt", "mimeType": "text/plain", "buffer": b"contenu de la note"}


def test_draft_stays_writable_during_a_turn(conversation: str, ask: Callable[[str], None], page: Page):
    draft = page.locator("#chatInput")
    send = page.locator("#chatSendBtn")
    stop = page.locator("#chatCancelBtn")

    ask("[hang] tour sans fin")
    expect(stop).to_be_visible()
    expect(draft).to_be_enabled()
    draft.fill("Brouillon")
    expect(send).to_be_disabled()
    draft.press("Enter")
    expect(page.locator(".event-user")).to_have_count(2)
    expect(draft).to_have_value("Brouillon")

    stop.click()
    expect(stop).to_be_hidden()
    expect(send).to_be_enabled()
    expect(page.get_by_text("Annulé par l'utilisateur")).to_be_visible()
    expect(draft).to_have_value("Brouillon")


def test_upload_is_not_a_turn(conversation: str, ask: Callable[[str], None], page: Page):
    held: list[Route] = []
    page.route("**/api/conversations/*/files", lambda route: held.append(route))
    page.locator("#chatFileInput").set_input_files(files=[NOTE])

    ask("Que contient ce fichier ?")
    expect(page.locator("#chatSendBtn")).to_be_disabled()
    expect(page.locator("#chatCancelBtn")).to_be_hidden()
    expect(page.locator("#chatInput")).to_be_enabled()

    while not held:
        page.wait_for_timeout(20)
    held[0].continue_()
    expect(page.locator(".event-final-answer")).to_have_count(2)
    expect(page.locator(".event-user .file-context-pill")).to_contain_text("note.txt")


def test_double_enter_creates_one_conversation(visit: Callable[[str], None], page: Page):
    held: list[Route] = []
    page.route(
        "**/api/conversations",
        lambda route: held.append(route) if route.request.method == "POST" else route.continue_(),
    )
    visit("/explorations/new")
    draft = page.locator("#chatInput")
    draft.fill("Question envoyée deux fois")
    draft.press("Enter")
    draft.press("Enter")
    page.wait_for_timeout(300)

    assert len(held) == 1
    held[0].continue_()
    expect(page).to_have_url(re.compile(r"/explorations/[0-9a-f-]{36}"))


def test_the_composer_is_drawn_from_its_state_when_the_page_loads(visit: Callable[[str], None], page: Page):
    # Why: Firefox restores a button's disabled state across reloads.
    page.add_init_script(
        "document.addEventListener('DOMContentLoaded', () => { document.getElementById('chatSendBtn').disabled = true; })"
    )
    visit("/explorations/new")
    expect(page.locator("#chatSendBtn")).to_be_enabled()


def test_back_to_a_new_conversation_starts_afresh(fake_agent, playwright: Playwright, base_url: str):
    # Why: Playwright turns the back-forward cache off; restoring /explorations/new from it is the case here.
    browser = playwright.chromium.launch(channel="chromium", ignore_default_args=["--disable-back-forward-cache"])
    page = browser.new_page(base_url=base_url)
    page.goto("/explorations/new", wait_until="domcontentloaded")
    page.locator("#chatInput").fill("Question avant le retour")
    page.locator("#chatInput").press("Enter")
    expect(page).to_have_url(re.compile(r"/explorations/[0-9a-f-]{36}"))

    page.go_back(wait_until="commit")
    expect(page.locator("#chatSendBtn")).to_be_enabled()
    assert page.evaluate("() => [performance.getEntriesByType('navigation')[0].type, currentConversationId]") == [
        "reload",
        None,
    ]
    browser.close()


def test_pending_files_do_not_follow_navigation(conversation: str, page: Page):
    uploads: list[str] = []
    page.on("request", lambda request: uploads.append(request.url) if request.url.endswith("/files") else None)
    page.locator("#chatFileInput").set_input_files(files=[NOTE])
    expect(page.locator(".pending-file")).to_have_count(1)

    page.locator("#sidebar a[href='/explorations/new']").click()
    expect(page).to_have_url(re.compile(r"/explorations/new"))
    page.wait_for_function("() => currentConversationId === null")
    page.locator("#chatInput").fill("Une autre question")
    page.locator("#chatInput").press("Enter")
    expect(page).to_have_url(re.compile(r"/explorations/[0-9a-f-]{36}"))

    assert uploads == []


def test_option_button_appends_to_the_draft(conversation: str, ask: Callable[[str], None], page: Page):
    ask("Que faire ?\n```options\nOui | Je confirme\nNon\n```")
    option = page.locator(".event-assistant .options-buttons button", has_text="Oui")
    expect(option).to_be_visible()

    draft = page.locator("#chatInput")
    draft.fill("Brouillon")
    option.click()

    expect(draft).to_have_value("Brouillon\n\nJe confirme")


def test_composer_buttons_stack_on_a_phone(conversation: str, ask: Callable[[str], None], page: Page):
    page.set_viewport_size({"width": 375, "height": 667})
    ask("[hang] tour sans fin")
    expect(page.locator("#chatCancelBtn")).to_be_visible()

    expect(page.locator("#chatFlagBtn")).to_be_hidden()
    send, stop = (page.locator(f"#{name}").bounding_box() for name in ("chatSendBtn", "chatCancelBtn"))
    composer = page.locator(".chat-input-wrapper").bounding_box()
    assert send["x"] == stop["x"]
    assert send["y"] < stop["y"]
    assert stop["y"] + stop["height"] - send["y"] == pytest.approx(composer["height"], abs=1)
    assert page.locator("#chatInput").bounding_box()["width"] > 220


def test_the_phone_composer_holds_two_lines_from_the_start(conversation: str, page: Page):
    page.set_viewport_size({"width": 375, "height": 667})
    composer = page.locator(".chat-input-wrapper")
    empty = composer.bounding_box()["height"]

    page.locator("#chatInput").fill("une\ndeux")
    assert composer.bounding_box()["height"] == empty
    page.locator("#chatInput").fill("une\ndeux\ntrois")
    assert composer.bounding_box()["height"] > empty
