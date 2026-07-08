"""Tests for the refactored primary navigation (sidebar + accueil grid)."""

import pytest


def headers(email="alice@example.com"):
    return {"X-Forwarded-Email": email}


def test_sidebar_has_reordered_links_and_tools_section(client):
    html = client.get("/", headers=headers()).text

    assert 'href="/explorations/new"' in html
    assert 'href="/conversations?show=convos"' in html
    assert 'href="/conversations?show=reports"' in html
    assert 'href="/jobs"' in html
    assert 'href="/cron"' in html
    assert 'href="/tag-manager"' in html
    assert "Aller plus loin" in html


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

    assert f'href="{active_href}" class="nav-link active"' in html
    assert f'href="{inactive_href}" class="nav-link active"' not in html
