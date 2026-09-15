"""Preuves navigateur — notification de fin de réponse : DOD-1, 3, 4, 5, 6 (le son : DOD-2, hermétique)."""

import re
from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser

BADGE = re.compile(r"^data:image/png")
BASE = re.compile(r"favicon\.png")


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


def set_focus(page: Page, focused: bool) -> None:
    page.evaluate(
        "(focused) => { Object.defineProperty(document, 'hasFocus', { configurable: true, value: () => focused }); }",
        focused,
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


def test_dod_1_badge_et_son_onglet_masque(visit: Callable[[str], None], page: Page):
    favicon = open_chat(visit, page)
    expect(favicon).to_have_count(1)
    spy_sound(page)
    set_hidden(page, True)
    finish_run(page)
    expect(favicon).to_have_attribute("href", BADGE)
    assert page.evaluate("() => window.__playCount") == 1


def test_dod_1_notifie_quand_autre_application(visit: Callable[[str], None], page: Page):
    favicon = open_chat(visit, page)
    spy_sound(page)
    set_hidden(page, False)
    set_focus(page, False)
    finish_run(page)
    expect(favicon).to_have_attribute("href", BADGE)
    assert page.evaluate("() => window.__playCount") == 1
    set_focus(page, True)
    page.evaluate("() => window.dispatchEvent(new Event('focus'))")
    expect(favicon).to_have_attribute("href", BASE)


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
    set_focus(page, True)
    finish_run(page)
    expect(favicon).to_have_attribute("href", BASE)
    assert page.evaluate("() => window.__playCount") == 0


def test_dod_5_erreur_agent_passe_par_le_meme_signal(visit: Callable[[str], None], page: Page):
    # Une erreur agent est stockée comme message assistant puis clôturée par
    # l'événement `done` (runner.py, stream.js) : c'est signalRunFinished() qui
    # notifie, exactement comme une fin nominale. DOD-5 découle donc de DOD-1 —
    # ici on prouve que signalRunFinished câble bien notifyRunFinished.
    favicon = open_chat(visit, page)
    set_hidden(page, True)
    page.evaluate("() => window.signalRunFinished()")
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
