"""Preuve navigateur — le lien vers le guide reste épinglé quand la conversation défile."""

import re
import uuid
from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser


def test_guide_banner_stays_in_viewport_after_scroll_to_bottom(visit: Callable[[str], None], page: Page):
    visit("/explorations/new")
    page.locator("#chatInput").fill(f"Question de bandeau {uuid.uuid4()}")
    page.locator("#chatSendBtn").click()
    expect(page).to_have_url(re.compile(r"/explorations/[0-9a-f-]{36}"))
    # Why: la fin du tour redessine la conversation et effacerait le bloc ajouté ci-dessous.
    expect(page.locator("#chatSendBtn")).to_be_enabled(timeout=30000)

    page.evaluate(
        "document.getElementById('chatOutput').insertAdjacentHTML('beforeend', '<div style=\"height: 5000px\"></div>');"
        "scrollToBottom();"
    )

    assert page.locator(".chat-main").evaluate("el => el.scrollTop") > 0
    expect(page.locator(".chat-guide-banner")).to_be_in_viewport()
