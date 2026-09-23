"""Preuve navigateur — le menu de filtres est en haut, façon recherche, pas en colonne (DOD-4)."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser


def test_dod_4_les_filtres_sont_en_haut_et_non_en_colonne_laterale(visit: Callable[[str], None], page: Page):
    visit("/conversations")

    bar = page.locator("#searchFilterBar")
    expect(bar).to_be_visible()

    assert page.locator(".filter-sidebar").count() == 0

    bar_box = bar.bounding_box()
    list_box = page.locator("#searchResultsList").bounding_box()
    assert bar_box is not None and list_box is not None
    assert bar_box["y"] <= list_box["y"]
