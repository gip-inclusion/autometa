"""Preuves navigateur — recherche et filtres des conversations et des tableaux de bord."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser


def test_les_filtres_des_conversations_sont_en_colonne_a_gauche_de_la_liste(visit: Callable[[str], None], page: Page):
    visit("/conversations")

    column = page.locator("#filterSidebar")
    expect(column).to_be_visible()

    column_box = column.bounding_box()
    list_box = page.locator("#searchResultsList").bounding_box()
    assert column_box is not None and list_box is not None
    assert column_box["x"] + column_box["width"] <= list_box["x"]


def test_la_frappe_lance_la_recherche_sans_quitter_le_champ(visit: Callable[[str], None], page: Page):
    visit("/conversations")
    field = page.locator("#rechercherSearchInput")

    field.press_sequentially("pass iae", delay=50)

    expect(page).to_have_url("/conversations?q=pass+iae")
    expect(field).to_be_focused()


def test_la_recherche_des_tableaux_de_bord_survit_a_un_detour_par_les_conversations(
    visit: Callable[[str], None], page: Page
):
    visit("/dashboards")
    for label in ("Conversations", "Tableaux de bord"):
        page.locator("a.nav-link:visible", has_text=label).first.click()
        expect(page.locator("h1")).to_contain_text(label)

    page.locator("#dashboardsSearchInput").press_sequentially("suivi")

    expect(page).to_have_url("/dashboards?q=suivi")
