"""Un tour complet contre le moteur factice : envoyer, recevoir, s'arrêter."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.browser, pytest.mark.usefixtures("fake_agent")]


def send(page: Page, text: str) -> None:
    page.locator("#chatInput").fill(text)
    page.locator("#chatInput").press("Enter")


def test_a_turn_streams_the_fake_answer(page: Page, visit):
    visit("/explorations/new")
    send(page, "bonjour")
    expect(page.locator("#chatOutput")).to_contain_text("Réponse factice : bonjour", timeout=15000)
    expect(page.locator("#chatSendBtn")).to_be_visible()


def test_stop_ends_a_hanging_turn_on_the_server(page: Page, visit):
    visit("/explorations/new")
    send(page, "[tools:1] [hang] attends")
    expect(page.locator(".action-pill").first).to_be_attached(timeout=15000)

    with page.expect_response("**/cancel") as cancel:
        page.locator("#chatCancelBtn").click()
    assert cancel.value.json() == {"status": "cancelled"}

    page.reload(wait_until="domcontentloaded")
    expect(page.locator("#chatOutput")).to_contain_text("Interrompu", timeout=10000)
    expect(page.locator("#chatOutput")).not_to_contain_text("Réponse factice")
    expect(page.locator("#chatSendBtn")).to_be_visible()
