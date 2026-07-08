"""Tests for the refactored primary navigation (sidebar + accueil grid)."""


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


def test_conversations_view_marks_conversations_active_not_reports(client):
    html = client.get("/conversations?show=convos", headers=headers()).text

    assert 'href="/conversations?show=convos" class="nav-link active"' in html
    assert 'href="/conversations?show=reports" class="nav-link active"' not in html


def test_reports_view_marks_reports_active_not_conversations(client):
    html = client.get("/conversations?show=reports", headers=headers()).text

    assert 'href="/conversations?show=reports" class="nav-link active"' in html
    assert 'href="/conversations?show=convos" class="nav-link active"' not in html
