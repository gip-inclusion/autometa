"""Parcours mobile — pas de défilement horizontal, en-tête compact, pas de zoom iOS sur la saisie."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser


@pytest.fixture
def phone(page: Page) -> Page:
    page.set_viewport_size({"width": 375, "height": 740})
    return page


@pytest.mark.parametrize("path", ["/", "/explorations/new", "/conversations?show=convos", "/dashboards"])
def test_no_horizontal_page_scroll_on_phone(visit: Callable[[str], None], phone: Page, path: str):
    visit(path)

    assert phone.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def test_chat_input_is_large_enough_to_avoid_ios_zoom(visit: Callable[[str], None], phone: Page):
    visit("/explorations/new")

    assert phone.locator("#chatInput").evaluate("e => parseFloat(getComputedStyle(e).fontSize)") >= 16


def test_new_conversation_is_reachable_from_home_on_phone(visit: Callable[[str], None], phone: Page):
    visit("/")

    expect(phone.locator(".accueil-button-primary")).to_be_visible()
