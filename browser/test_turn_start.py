"""Preuve navigateur — un envoi refusé parce qu'un tour est déjà en cours rend le texte à la barre de saisie."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser


def test_send_refused_while_running_restores_the_draft(conversation: str, ask: Callable[[str], None], page: Page):
    started = page.request.post(
        f"/api/conversations/{conversation}/messages", data={"content": "[hang] tour lancé ailleurs"}
    )
    assert started.ok, started.text()

    ask("Question de l'onglet en retard")

    expect(page.locator(".event-error")).to_have_text("Une réponse est déjà en cours dans cette conversation.")
    expect(page.locator(".event-user")).to_have_count(1)
    expect(page.locator("#chatInput")).to_have_value("Question de l'onglet en retard")
