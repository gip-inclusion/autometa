"""Tests for rapports routes.

Tests the /rapports/ endpoints including the .txt export feature.
"""

import pytest


@pytest.fixture
def report(app):
    from web.database import store

    report = store.create_report(
        title="Test Report",
        content="---\ndate: 2026-01-01\nwebsite: test\n---\n\n# Test Report\n\nThis is **markdown** content.",
        website="test",
        category="testing",
        user_id="test@example.com",
    )
    return report


@pytest.fixture
def conversation(app):
    from web.database import store

    return store.create_conversation(user_id="test@example.com")


@pytest.fixture
def report_with_source(app, conversation):
    from web.database import store

    return store.create_report(
        title="Linked Report",
        content="# Linked\n\nContent.",
        website="test",
        category="testing",
        user_id="test@example.com",
        source_conversation_id=conversation.id,
    )


def test_rapport_txt_export_returns_plain_text(app, client, report):
    """GET /rapports/<id>.txt returns text/plain content type."""
    response = client.get(
        f"/rapports/{report.id}.txt",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")


def test_rapport_txt_export_returns_raw_markdown(app, client, report):
    """GET /rapports/<id>.txt returns the raw markdown content."""
    response = client.get(
        f"/rapports/{report.id}.txt",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "# Test Report" in content
    assert "**markdown**" in content
    assert "date: 2026-01-01" in content


def test_rapport_txt_export_nonexistent_report_returns_404(app, client):
    """GET /rapports/<nonexistent>.txt returns 404."""
    response = client.get(
        "/rapports/99999.txt",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert response.status_code == 404


def test_rapport_txt_export_utf8_encoding(app, client):
    """GET /rapports/<id>.txt handles UTF-8 content correctly."""
    from web.database import store

    report = store.create_report(
        title="Rapport avec accents",
        content="# Résumé\n\nCe rapport contient des caractères spéciaux: é, è, ê, ë, à, ç, ù.",
        website="test",
        category="testing",
        user_id="test@example.com",
    )

    response = client.get(
        f"/rapports/{report.id}.txt",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Résumé" in content
    assert "é, è, ê, ë, à, ç, ù" in content


def test_rapport_detail_view_has_export_button(app, client, report):
    """Report detail view includes the 'Version exportable' button."""
    response = client.get(
        f"/rapports/{report.id}",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert response.status_code == 200
    assert b"Version exportable" in response.content
    assert f"/rapports/{report.id}.txt".encode() in response.content


def test_rapport_detail_view_has_continue_button(app, client, report):
    """Report detail view still includes the 'Poursuivre l'exploration' button."""
    response = client.get(
        f"/rapports/{report.id}",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert response.status_code == 200
    assert b"Poursuivre l'exploration" in response.content


def test_rapports_list_redirects_to_rechercher(app, client, report):
    """/rapports redirects to /rechercher?show=reports."""
    response = client.get(
        "/rapports",
        headers={"X-Forwarded-Email": "test@example.com"},
        follow_redirects=False,
    )
    assert response.status_code == 301
    assert response.headers["location"] == "/rechercher?show=reports"


def _extract_main_content(html: str) -> str:
    import re

    main_match = re.search(r'<main[^>]*\bid="main"[^>]*>', html)
    assert main_match, "Could not find <main id='main'> in response"
    start = main_match.end()
    end = html.find("</main>", start)
    assert end != -1, "Could not find </main>"
    return html[start:end]


def _report_body_has_content(main_html: str) -> bool:
    import re

    match = re.search(
        r'<div[^>]*\bid="reportBody"[^>]*>(.*?)</div>',
        main_html,
        re.DOTALL,
    )
    if not match:
        return False
    body_content = match.group(1).strip()
    return len(body_content) > 0


def test_rapport_htmx_report_rendering_survives_htmx_swap(app, client, report):
    """After HTMX swaps #main, report content must be in the DOM."""
    response = client.get(
        f"/rapports/{report.id}",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    main_content = _extract_main_content(html)

    assert _report_body_has_content(main_content), (
        "Report body is empty inside #main. Content must be server-side rendered so it survives HTMX navigation."
    )


def test_rapport_htmx_report_list_items_use_htmx_boost(app, client, report):
    """Report list in /rechercher has hx-boost for HTMX navigation."""
    response = client.get(
        "/rechercher?show=reports",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    html = response.content.decode("utf-8")
    main_content = _extract_main_content(html)

    assert 'hx-boost="true"' in main_content
    assert 'hx-target="#main"' in main_content
    assert 'hx-select="#main > *"' in main_content


def test_rapport_htmx_report_detail_has_rendered_html_in_main(app, client, report):
    """The rendered HTML must be inside #main for HTMX swaps."""
    response = client.get(
        f"/rapports/{report.id}",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    html = response.content.decode("utf-8")
    main_content = _extract_main_content(html)

    assert "<h1" in main_content, "Heading should be rendered as HTML"
    assert "<strong>markdown</strong>" in main_content, "Bold should be rendered as HTML"
    assert "---\ndate:" not in main_content


def test_report_author_in_search_shows_author(app, client, report):
    """Report author (user_id) appears in search results."""
    response = client.get(
        "/rechercher?show=reports",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    html = response.content.decode("utf-8")
    assert "conv-item-author" in html
    assert "test" in html  # test@example.com -> "test"


def test_report_author_in_search_shows_source_conversation_link(app, client, report_with_source, conversation):
    """Report with source_conversation_id shows a conversation link."""
    response = client.get(
        "/rechercher?show=reports",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    html = response.content.decode("utf-8")
    assert f"/explorations/{conversation.id}" in html
    assert "Conversation" in html


def test_report_author_in_search_without_source_has_no_conversation_link(app, client, report):
    """Report without source_conversation_id has no conversation link."""
    response = client.get(
        "/rechercher?show=reports",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    html = response.content.decode("utf-8")
    main_content = _extract_main_content(html)
    assert "/explorations/" not in main_content


def test_report_author_in_search_is_searchable(app, client, report):
    """Report author appears in data-search attribute for client-side filtering."""
    response = client.get(
        "/rechercher?show=reports",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    html = response.content.decode("utf-8")
    assert 'data-search="' in html
    assert "test@example.com" in html
