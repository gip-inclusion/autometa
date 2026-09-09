"""Preuves navigateur — notification de fin de réponse : DOD-1, 3, 4, 5, 6 (le son : DOD-2, hermétique)."""

import re
from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser

BADGE = re.compile(r"^data:image/png")
BASE = re.compile(r"favicon\.svg")


def open_chat(visit: Callable[[str], None], page: Page):
    visit("/explorations/new")
    return page.locator("#appFavicon")


def set_hidden(page: Page, hidden: bool) -> None:
    page.evaluate(
        """(hidden) => {
            Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden });
            Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => hidden ? 'hidden' : 'visible' });
            document.dispatchEvent(new Event('visibilitychange'));
        }""",
        hidden,
    )


def spy_sound(page: Page) -> None:
    page.evaluate(
        """() => {
            window.__playCount = 0;
            HTMLMediaElement.prototype.play = function () { window.__playCount++; return Promise.resolve(); };
        }"""
    )


def finish_run(page: Page) -> None:
    page.evaluate("() => window.notifyRunFinished()")


def test_dod_1_badge_apparait_onglet_masque(visit: Callable[[str], None], page: Page):
    favicon = open_chat(visit, page)
    expect(favicon).to_have_count(1)
    set_hidden(page, True)
    finish_run(page)
    expect(favicon).to_have_attribute("href", BADGE)


def test_dod_3_badge_disparait_au_retour(visit: Callable[[str], None], page: Page):
    favicon = open_chat(visit, page)
    set_hidden(page, True)
    finish_run(page)
    expect(favicon).to_have_attribute("href", BADGE)
    set_hidden(page, False)
    expect(favicon).to_have_attribute("href", BASE)


def test_dod_4_rien_si_onglet_actif(visit: Callable[[str], None], page: Page):
    favicon = open_chat(visit, page)
    spy_sound(page)
    set_hidden(page, False)
    finish_run(page)
    expect(favicon).to_have_attribute("href", BASE)
    assert page.evaluate("() => window.__playCount") == 0


def test_dod_5_notifie_aussi_sur_erreur(visit: Callable[[str], None], page: Page):
    favicon = open_chat(visit, page)
    set_hidden(page, True)
    page.evaluate(
        """() => {
            const out = document.getElementById('chatOutput');
            if (out) out.insertAdjacentHTML('beforeend', '<div class="event-block event-error">Erreur</div>');
            window.notifyRunFinished();
        }"""
    )
    expect(favicon).to_have_attribute("href", BADGE)


def test_dod_6_point_unique_sans_compteur(visit: Callable[[str], None], page: Page):
    favicon = open_chat(visit, page)
    set_hidden(page, True)
    finish_run(page)
    expect(favicon).to_have_attribute("href", BADGE)
    once = favicon.get_attribute("href")
    finish_run(page)
    finish_run(page)
    expect(favicon).to_have_attribute("href", BADGE)
    assert favicon.get_attribute("href") == once
