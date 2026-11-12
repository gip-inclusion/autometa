"""Preuves navigateur — messages en attente : envoyés plus tard, repris, rendus à la barre de saisie."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser


def queue_through_the_api(page: Page, conversation: str, text: str) -> None:
    response = page.request.post(f"/api/conversations/{conversation}/messages", data={"content": text, "queue": True})
    assert response.json()["status"] == "queued"


def start_turn(ask: Callable[[str], None], page: Page, question: str) -> None:
    ask(question)
    expect(page.locator("#chatCancelBtn")).to_be_visible()


def test_questions_sent_by_the_server_join_the_conversation(conversation: str, ask: Callable[[str], None], page: Page):
    start_turn(ask, page, "[slow:2] q0")

    queue_through_the_api(page, conversation, "q1")

    expect(page.locator(".event-final-answer").last).to_contain_text("Réponse factice : q1", timeout=15000)
    expect(page.locator("#chatOutput .event-user")).to_have_text(["Première question", "[slow:2] q0", "q1"])
    expect(page.locator(".event-final-answer")).to_have_count(3)
