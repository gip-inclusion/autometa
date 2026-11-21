"""Preuves navigateur — le lien vers le guide défile avec la conversation et reste caché sur téléphone."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser


def test_guide_banner_scrolls_away_with_the_conversation(visit: Callable[[str], None], page: Page):
    visit("/c/new")
    banner = page.locator(".chat-guide-banner")
    expect(banner).to_be_in_viewport()

    page.evaluate(
        "document.getElementById('chatOutput').insertAdjacentHTML('beforeend', '<div style=\"height: 5000px\"></div>');"
        "scrollToBottom();"
    )

    expect(banner).not_to_be_in_viewport()


def test_guide_icon_sits_on_the_first_line(visit: Callable[[str], None], page: Page):
    page.set_viewport_size({"width": 992, "height": 800})
    visit("/c/new")
    icon = page.locator(".chat-guide-banner > i").bounding_box()
    lines = page.locator(".chat-guide-banner > a").evaluate(
        "a => { const text = document.createRange(); text.selectNodeContents(a);"
        " return [...text.getClientRects()].map((line) => ({ top: line.top, bottom: line.bottom })); }"
    )

    assert len(lines) > 1, "le texte doit tenir sur plusieurs lignes à 992 px pour que le test ait un sens"
    assert lines[0]["top"] <= icon["y"] + icon["height"] / 2 <= lines[0]["bottom"]


def test_guide_banner_has_as_much_space_below_as_above(visit: Callable[[str], None], page: Page):
    visit("/c/new")
    above, below = page.locator(".chat-guide-banner > a").evaluate(
        "a => { const text = document.createRange(); text.selectNodeContents(a); const lines = text.getClientRects();"
        " const top = document.querySelector('.chat-main').getBoundingClientRect().top;"
        " const next = document.querySelector('#chatOutput').firstElementChild.getBoundingClientRect().top;"
        " return [lines[0].top - top, next - lines[lines.length - 1].bottom]; }"
    )

    assert below == pytest.approx(above, abs=3)


def test_guide_banner_is_hidden_on_a_phone(visit: Callable[[str], None], page: Page):
    page.set_viewport_size({"width": 375, "height": 667})
    visit("/c/new")

    expect(page.locator("#chatInput")).to_be_visible()
    expect(page.locator(".chat-guide-banner")).to_be_hidden()
