"""Socle de non-régression : les parcours que toute fonctionnalité future traverse.

Écrits avant le premier test `DOD-N`, sans quoi la suite ne défendrait rien au jour 1.
Voir docs/paved-road/l3-e2e.md.
"""

import re
import uuid
from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser


def create_report(page: Page) -> tuple[int, str]:
    """Un rapport neuf, créé par la surface HTTP de l'application — donc valable aussi sur une review app."""
    title = f"Rapport de socle {uuid.uuid4()}"
    response = page.request.post("/api/reports", data={"title": title, "content": "# Section\n\nCorps du rapport."})
    assert response.status == 201, response.text()
    return response.json()["id"], title


def test_home_page_serves_the_application(visit: Callable[[str], None], page: Page):
    visit("/")

    expect(page.get_by_role("heading", name="Accueil")).to_be_visible()


def test_first_message_creates_a_conversation(visit: Callable[[str], None], page: Page):
    visit("/explorations/new")

    question = f"Question de socle {uuid.uuid4()}"
    page.locator("#chatInput").fill(question)
    page.locator("#chatSendBtn").click()

    expect(page).to_have_url(re.compile(r"/explorations/[0-9a-f-]{36}"))
    expect(page.get_by_text(question)).to_be_visible()


def test_a_report_opens_from_the_reports_list(visit: Callable[[str], None], page: Page):
    report_id, title = create_report(page)

    visit("/conversations?show=reports")
    page.locator(f"#report-{report_id}").get_by_text(title).click()

    expect(page).to_have_url(re.compile(rf"/rapports/{report_id}$"))
    expect(page.get_by_role("heading", name=title)).to_be_visible()
    expect(page.get_by_text("Corps du rapport.")).to_be_visible()


def test_selftest_streams_service_checks(visit: Callable[[str], None], page: Page):
    visit("/selftest")

    expect(page.locator("#out")).to_contain_text(re.compile(r"✅ PostgreSQL"), timeout=30_000)


def test_dashboards_list_renders(visit: Callable[[str], None], page: Page):
    visit("/dashboards")

    expect(page.get_by_role("heading", name="Tableaux de bord")).to_be_visible()
