"""Un tour complet contre le moteur factice : envoyer, recevoir, s'arrêter."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.browser, pytest.mark.usefixtures("fake_agent")]


def test_a_turn_streams_the_fake_answer(page: Page, visit, ask: Callable[[str], None]):
    visit("/explorations/new")
    ask("bonjour")
    expect(page.locator("#chatOutput")).to_contain_text("Réponse factice : bonjour", timeout=15000)
    expect(page.locator("#chatSendBtn")).to_be_enabled()


def test_stop_ends_a_hanging_turn_on_the_server(page: Page, visit, ask: Callable[[str], None]):
    visit("/explorations/new")
    ask("[tools:1] [hang] attends")
    expect(page.locator(".action-pill").first).to_be_attached(timeout=15000)

    with page.expect_response("**/cancel") as cancel:
        page.locator("#chatCancelBtn").click()
    assert cancel.value.json() == {"status": "cancelled"}

    page.reload(wait_until="domcontentloaded")
    expect(page.locator("#chatOutput")).to_contain_text("Interrompu", timeout=10000)
    expect(page.locator("#chatOutput")).not_to_contain_text("Réponse factice")
    expect(page.locator("#chatSendBtn")).to_be_enabled()
