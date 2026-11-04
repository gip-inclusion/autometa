"""Preuve navigateur — taper `@` dans le chat propose les jobs, et en choisir un complète la mention (DOD-5)."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page, Route, expect

pytestmark = pytest.mark.browser


def test_dod_5_taper_arobase_propose_les_jobs_et_complete_la_mention(visit: Callable[[str], None], page: Page):
    # Why: le service de jobs est externe ; seule sa liste de noms est simulée, l'interface est réelle.
    def names(route: Route) -> None:
        route.fulfill(json={"names": ["boamp-veille", "veille-dora", "veille-emplois"]})

    page.route("**/api/jobs/pipelines/names", names)
    sent = []
    page.on("request", lambda r: sent.append(r.url) if r.method == "POST" and "/messages" in r.url else None)
    visit("/explorations/new")

    chat = page.locator("#chatInput")
    chat.click()
    chat.press_sequentially("que donne @veil")

    options = page.locator("#jobMentions [role=option]")
    expect(options).to_have_text(["@veille-dora", "@veille-emplois"])

    chat.press("ArrowDown")
    chat.press("Enter")

    expect(chat).to_have_value("que donne @veille-emplois ")
    expect(page.locator("#jobMentions")).to_be_hidden()
    assert sent == []
