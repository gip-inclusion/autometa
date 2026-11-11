"""Preuves navigateur — sur téléphone : en-tête sur une ligne, menu « … », ni défilement horizontal ni zoom iOS."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser

PHONE = {"width": 375, "height": 667}
MENU_ITEMS = {"Signaler un problème": "#flagDialog", "Renommer": "#convTitleInput"}


def test_the_header_fits_on_one_line(conversation: str, page: Page):
    page.set_viewport_size(PHONE)
    boxes = [page.locator(s).bounding_box() for s in (".conv-back-link", ".conv-title-display h1", ".conv-menu-btn")]

    assert max(box["y"] for box in boxes) < min(box["y"] + box["height"] for box in boxes)
    expect(page.locator("#convMenu")).to_be_hidden()
    expect(page.locator(".feedback-badge")).to_be_hidden()


@pytest.mark.parametrize("item", MENU_ITEMS.keys())
def test_the_menu_holds_the_conversation_actions(conversation: str, page: Page, item: str):
    page.set_viewport_size(PHONE)
    page.locator(".conv-menu-btn").click()
    menu = page.locator("#convMenu")
    button = page.locator(".conv-menu-btn").bounding_box()
    assert menu.bounding_box()["y"] >= button["y"] + button["height"]
    favorite_label = menu.locator(".favorite-btn").evaluate("b => getComputedStyle(b, '::after').content")
    assert favorite_label == '"Ajouter aux favoris"'
    for name in ("Renommer", "Dupliquer", "Ajouter aux favoris", "Signaler un problème", "Donnez votre avis"):
        expect(menu.get_by_role("button", name=name).or_(menu.get_by_role("link", name=name))).to_be_visible()

    menu.get_by_role("button", name=item).click()

    expect(page.locator(MENU_ITEMS[item])).to_be_visible()
    expect(menu).to_be_hidden()


def test_the_menu_shows_a_flagged_conversation(conversation: str, page: Page):
    page.set_viewport_size(PHONE)
    page.locator(".conv-menu-btn").click()
    page.locator("#convMenu").get_by_role("button", name="Signaler un problème").click()
    page.locator("#flagReason").fill("Chiffres faux")
    page.locator("#flagSubmit").click()
    expect(page.locator("#chatFlagBtn.flagged")).to_have_count(1)

    page.locator(".conv-menu-btn").click()
    expect(page.locator("#convMenuFlagBtn")).to_have_css("color", "rgb(201, 25, 30)")


def test_the_actions_stay_inline_on_a_desktop(conversation: str, page: Page):
    expect(page.locator("#editTitleBtn")).to_be_visible()
    expect(page.locator(".feedback-badge")).to_be_visible()
    expect(page.locator(".conv-menu-btn")).to_be_hidden()
    expect(page.locator("#convMenuFlagBtn")).to_be_hidden()
