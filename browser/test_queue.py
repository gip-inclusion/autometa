"""Preuves navigateur — messages en attente : envoyés plus tard, repris, rendus à la barre de saisie."""

import re
from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser

NOTE = {"name": "note.txt", "mimeType": "text/plain", "buffer": b"contenu de la note"}


def queue_through_the_api(page: Page, conversation: str, text: str) -> None:
    response = page.request.post(f"/api/conversations/{conversation}/messages", data={"content": text, "queue": True})
    assert response.json()["status"] == "queued"


def start_turn(ask: Callable[[str], None], page: Page, question: str) -> None:
    ask(question)
    expect(page.locator("#chatCancelBtn")).to_be_visible()


def send_later(page: Page, text: str) -> None:
    page.locator("#chatInput").fill(text)
    page.locator("#chatInput").press("Enter")


def come_back(page: Page, conversation: str, how: str) -> Page:
    """La conversation rouverte par un rechargement, un autre onglet ou une visite ailleurs."""
    if how == "rechargement":
        page.reload(wait_until="domcontentloaded")
        return page
    if how == "autre onglet":
        other = page.context.new_page()
        other.goto(f"/explorations/{conversation}", wait_until="domcontentloaded")
        return other
    page.locator("#sidebar a[href='/explorations/new']").click()
    expect(page).to_have_url(re.compile(r"/explorations/new$"))
    page.locator(f"#sidebar a[href='/explorations/{conversation}']").first.click()
    return page


def test_questions_sent_by_the_server_join_the_conversation(conversation: str, ask: Callable[[str], None], page: Page):
    start_turn(ask, page, "[slow:2] q0")

    queue_through_the_api(page, conversation, "q1")

    expect(page.locator(".event-final-answer").last).to_contain_text("Réponse factice : q1", timeout=15000)
    expect(page.locator("#chatOutput .event-user")).to_have_text(["Première question", "[slow:2] q0", "q1"])
    expect(page.locator(".event-final-answer")).to_have_count(3)


@pytest.mark.parametrize("queued", [["q1"], ["q1", "q2"]], ids=["un message", "deux messages"])
def test_messages_sent_later_leave_together_when_the_turn_ends(
    conversation: str, ask: Callable[[str], None], page: Page, queued: list[str]
):
    send = page.locator("#chatSendBtn")
    start_turn(ask, page, "[slow:3] q0")
    expect(send).to_have_attribute("title", "Envoyer plus tard")

    for count, text in enumerate(queued, 1):
        send_later(page, text)
        expect(page.locator(".event-queued")).to_have_count(count)

    expect(page.locator(".event-queued")).to_have_text(queued)
    expect(page.locator("#chatInput")).to_have_value("")
    expect(page.locator(".event-final-answer").last).to_contain_text(f"Réponse factice : {queued[-1]}", timeout=15000)
    expect(page.locator(".event-queued")).to_have_count(0)
    expect(page.locator("#chatOutput .event-user")).to_have_text(["Première question", "[slow:3] q0", *queued])
    expect(page.locator(".event-final-answer")).to_have_count(3)
    expect(send).to_have_attribute("title", "Envoyer")


@pytest.mark.parametrize("how", ["rechargement", "autre onglet", "visite ailleurs"])
def test_a_waiting_message_is_still_there_when_coming_back(
    conversation: str, ask: Callable[[str], None], page: Page, how: str
):
    start_turn(ask, page, "[hang] q0")
    send_later(page, "q1")
    expect(page.locator(".event-queued")).to_have_text(["q1"])

    back = come_back(page, conversation, how)

    expect(back.locator(".event-queued")).to_have_text(["q1"])
    expect(back.locator("#chatSendBtn")).to_have_attribute("title", "Envoyer plus tard")


def test_another_tab_sees_messages_queued_here(conversation: str, ask: Callable[[str], None], page: Page):
    start_turn(ask, page, "[hang] q0")
    other = come_back(page, conversation, "autre onglet")
    expect(other.locator("#chatCancelBtn")).to_be_visible()

    send_later(page, "q1")

    expect(other.locator(".event-queued")).to_have_text(["q1"])


@pytest.mark.parametrize(
    ("target", "bar"),
    [(".event-queued", "Brouillon\n\nq1"), (".queued-remove", "Brouillon")],
    ids=["reprendre", "retirer"],
)
def test_a_waiting_message_can_be_pulled_back_or_dropped(
    conversation: str, ask: Callable[[str], None], page: Page, target: str, bar: str
):
    start_turn(ask, page, "[slow:3] q0")
    send_later(page, "q1")
    page.locator("#chatInput").fill("Brouillon")

    page.locator(target).click()

    expect(page.locator("#chatInput")).to_have_value(bar)
    expect(page.locator(".event-queued")).to_have_count(0)
    expect(page.locator("#chatCancelBtn")).to_be_hidden(timeout=15000)
    expect(page.locator("#chatOutput .event-user")).to_have_count(2)


def test_a_double_click_pulls_a_message_back_once(conversation: str, ask: Callable[[str], None], page: Page):
    start_turn(ask, page, "[hang] q0")
    send_later(page, "q1")

    with page.expect_response("**/queue/*"):
        page.locator(".event-queued").dblclick()

    expect(page.locator("#chatInput")).to_have_value("q1")
    expect(page.locator(".event-error")).to_have_count(0)


def test_stop_puts_waiting_messages_back_in_the_bar_once(conversation: str, ask: Callable[[str], None], page: Page):
    draft = page.locator("#chatInput")
    held = []
    start_turn(ask, page, "[hang] q0")
    send_later(page, "q1")
    expect(page.locator(".event-queued")).to_have_count(1)
    draft.fill("Brouillon")
    # Why: the stream hands the messages back first, then the Stop response does again.
    page.route("**/cancel", lambda route: held.append((route, route.fetch())))

    with page.expect_response("**/queue/returned/ack"):
        page.locator("#chatCancelBtn").click()
    route, response = held[0]
    route.fulfill(response=response)

    expect(page.get_by_text("Annulé par l'utilisateur")).to_be_visible()
    expect(draft).to_have_value("Brouillon\n\nq1")
    expect(page.locator(".event-queued")).to_have_count(0)
    page.reload(wait_until="domcontentloaded")
    expect(page.locator("#chatOutput .event-user")).to_have_count(2)
    expect(draft).to_have_value("")


def test_a_failed_turn_puts_waiting_messages_back_in_the_bar(conversation: str, ask: Callable[[str], None], page: Page):
    start_turn(ask, page, "[slow:2] [error] q0")
    send_later(page, "q1")

    expect(page.get_by_text("Erreur factice")).to_be_visible(timeout=15000)
    expect(page.locator("#chatInput")).to_have_value("q1")
    expect(page.locator(".event-queued")).to_have_count(0)


def test_nothing_is_sent_while_a_stop_is_in_progress(conversation: str, ask: Callable[[str], None], page: Page):
    held = []
    start_turn(ask, page, "[hang] q0")
    page.route("**/cancel", lambda route: held.append(route))
    page.locator("#chatCancelBtn").click()
    while not held:
        page.wait_for_timeout(20)

    send_later(page, "Pendant l'arrêt")

    expect(page.locator("#chatSendBtn")).to_be_disabled()
    expect(page.locator("#chatInput")).to_have_value("Pendant l'arrêt")
    held[0].continue_()
    expect(page.locator("#chatCancelBtn")).to_be_hidden()
    expect(page.locator(".event-queued")).to_have_count(0)


def test_files_cannot_be_attached_during_a_turn(conversation: str, ask: Callable[[str], None], page: Page):
    start_turn(ask, page, "[hang] q0")

    page.locator("#chatFileInput").set_input_files(files=[NOTE])

    expect(page.locator("#chatUploadBtn")).to_be_disabled()
    expect(page.locator("#chatPendingFiles")).to_be_empty()


def test_a_waiting_message_fits_a_phone(conversation: str, ask: Callable[[str], None], page: Page):
    page.set_viewport_size({"width": 375, "height": 667})
    start_turn(ask, page, "[hang] q0")

    send_later(page, "Et par département, avec la part des femmes et des moins de 26 ans ?")

    bubble = page.locator(".event-queued").bounding_box()
    assert bubble["x"] >= 0
    assert bubble["x"] + bubble["width"] <= 375
    assert page.evaluate("document.documentElement.scrollWidth") <= 375
