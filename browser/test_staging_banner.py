"""Preuve navigateur — le message du bandeau de test tient dans le bandeau sur téléphone."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.browser


# Why: skip hors staging et review app (où tourne la CI browser) : en local le bandeau est absent.
@pytest.mark.parametrize("width", [390, 1440])
def test_staging_banner_text_fits(visit: Callable[[str], None], page: Page, width: int):
    page.set_viewport_size({"width": width, "height": 800})
    visit("/")
    banner = page.locator(".staging-banner")
    if not banner.count():
        pytest.skip("bandeau absent : instance servie hors staging et review app")
    assert banner.evaluate("el => el.scrollHeight <= el.clientHeight")
