"""Preuves navigateur — sur téléphone : en-tête sur une ligne, menu « … », nouvelle conversation depuis l'accueil, ni défilement horizontal ni zoom iOS."""

import re
from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser

PHONE = {"width": 375, "height": 667}
MENU_ITEMS = {"Signaler un problème": "#flagDialog", "Renommer": "#convTitleInput"}
WIDE_TABLE = (
    "| colonne A | colonne B | colonne C | colonne D | colonne E | colonne F | colonne G | colonne H |\n"
    "|---|---|---|---|---|---|---|---|\n"
    "| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |"
)
LONG_URL = "https://matomo.example.org/index.php?module=CoreHome&action=index&idSite=117&period=day&date=yesterday"
OTHER_PAGES = {
    "/conversations": ".search-filter-bar .rechercher-type-btn",
    "/dashboards": ".section-header .btn-primary",
    "/knowledge/bizdev/glossaire.md": ".markdown-body table",
}


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


def test_the_home_page_starts_a_conversation_without_the_sidebar(visit: Callable[[str], None], page: Page):
    page.set_viewport_size(PHONE)
    visit("/")
    grid = page.locator(".accueil-button-grid")
    tile = grid.locator("a:visible").first
    expect(tile).to_have_text("Nouvelle conversation")
    assert tile.bounding_box()["width"] == pytest.approx(grid.bounding_box()["width"])

    tile.click()

    expect(page).to_have_url(re.compile(r"/explorations/new$"))
    expect(page.locator("#chatInput")).to_be_visible()


def test_the_home_page_leaves_new_conversations_to_the_sidebar_on_a_desktop(visit: Callable[[str], None], page: Page):
    visit("/")

    expect(page.locator(".accueil-button-grid a:visible").first).to_have_text("Toutes les conversations")


def right_edge(page: Page, selector: str) -> float:
    return max(page.locator(selector).evaluate_all("els => els.map((el) => el.getBoundingClientRect().right)"))


def test_nothing_sticks_out_sideways_on_a_small_phone(conversation: str, ask: Callable[[str], None], page: Page):
    page.set_viewport_size({"width": 320, "height": 640})
    ask(f"Un tableau large et un lien long\n\n{WIDE_TABLE}\n\n<{LONG_URL}>")
    table = page.locator(".event-final-answer table")
    expect(table).to_be_visible()

    links = (".event-user a", ".event-final-answer a")
    for selector in (".chat-bar-container", ".chat-output", ".event-user", ".event-final-answer table", *links):
        assert right_edge(page, selector) <= 320, selector
    assert table.evaluate("t => t.scrollWidth > t.clientWidth")
    for path, selector in OTHER_PAGES.items():
        page.goto(path, wait_until="domcontentloaded")
        assert right_edge(page, selector) <= 320, path


@pytest.mark.parametrize("viewport", [PHONE, {"width": 844, "height": 390}], ids=["portrait", "paysage"])
def test_text_fields_are_large_enough_for_ios_not_to_zoom(conversation: str, page: Page, base_url: str, viewport: dict):
    touch = page.context.browser.new_page(base_url=base_url, viewport=viewport, is_mobile=True, has_touch=True)
    touch.goto(f"/explorations/{conversation}", wait_until="domcontentloaded")

    sizes = touch.locator("input[type=text], textarea, select").evaluate_all(
        "fields => fields.map((field) => parseFloat(getComputedStyle(field).fontSize))"
    )
    assert len(sizes) >= 3
    assert min(sizes) >= 16
    touch.close()
