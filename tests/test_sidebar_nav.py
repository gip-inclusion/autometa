"""Tests for the refactored primary navigation (sidebar + accueil grid)."""

import re

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]


def headers(email="alice@example.com"):
    return {"X-Forwarded-Email": email}


def first_link_tag(html, href):
    match = re.search(r'<a href="' + re.escape(href) + r'"[^>]*>', html)
    return match.group(0) if match else ""


def test_sidebar_has_reordered_links_and_tools_section(client):
    html = client.get("/", headers=headers()).text

    assert 'href="/explorations/new"' in html
    assert 'href="/conversations?show=convos"' in html
    assert 'href="/conversations?show=reports"' in html
    assert 'href="/jobs"' in html
    assert 'href="/cron"' in html
    assert 'href="/tag-manager"' in html
    assert "Aller plus loin" in html


def test_tools_links_have_hover_definitions(client):
    html = client.get("/", headers=headers()).text

    assert 'title="Analyses autonomes longues lancées en arrière-plan (minutes à heures)"' in html
    assert 'title="Tâches planifiées récurrentes (rafraîchissement des tableaux de bord, synchronisations)"' in html
    assert 'title="Gestion des balises Matomo Tag Manager (déclencheurs, tags, déploiements)"' in html
    assert 'data-bs-toggle="tooltip"' in html


def test_sidebar_drops_accueil_nav_link(client):
    html = client.get("/", headers=headers()).text

    assert 'href="/" class="nav-link' not in html
    assert 'href="/" class="sidebar-brand"' in html


def test_accueil_grid_drops_technical_tools_keeps_rapports(client):
    html = client.get("/", headers=headers()).text

    assert 'href="/jobs" class="accueil-button"' not in html
    assert 'href="/cron" class="accueil-button"' not in html
    assert 'href="/tag-manager" class="accueil-button"' not in html
    assert 'href="/conversations?show=reports" class="accueil-button"' in html
    assert 'href="/dashboards" class="accueil-button"' in html


@pytest.mark.parametrize(
    ("url", "active_href", "inactive_href"),
    [
        ("/conversations?show=convos", "/conversations?show=convos", "/conversations?show=reports"),
        ("/conversations?show=reports", "/conversations?show=reports", "/conversations?show=convos"),
    ],
)
def test_active_tab_matches_current_view(client, url, active_href, inactive_href):
    html = client.get(url, headers=headers()).text

    assert 'aria-current="page"' in first_link_tag(html, active_href)
    assert 'aria-current="page"' not in first_link_tag(html, inactive_href)


def test_report_detail_marks_reports_tab_active(app, client):
    from web.database import store

    report = store.create_report(
        title="Test Report",
        content="# Test",
        website="test",
        category="testing",
        user_id="alice@example.com",
    )
    html = client.get(f"/rapports/{report.id}", headers=headers()).text

    assert 'aria-current="page"' in first_link_tag(html, "/conversations?show=reports")
    assert 'aria-current="page"' not in first_link_tag(html, "/conversations?show=convos")
