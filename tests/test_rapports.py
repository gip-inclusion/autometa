"""Tests for rapports routes.

Tests the /rapports/ endpoints including the markdown download.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]


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


def make_report(title, content="---\ndate: 2026-01-01\n---\n\n# Titre\n\nDu **markdown**."):
    from web.database import store

    return store.create_report(
        title=title,
        content=content,
        website="test",
        category="testing",
        user_id="test@example.com",
    )


def test_rapport_markdown_is_served_as_a_download(app, client, report):
    """DOD-1 — un clic télécharge un fichier au lieu d'afficher le texte dans un onglet."""
    response = client.get(
        f"/rapports/{report.id}.md",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["content-disposition"].startswith("attachment;")


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Bilan mensuel des candidatures", "bilan-mensuel-des-candidatures.md"),
        ("Rapport « été 2026 » — pass IAE", "rapport-ete-2026-pass-iae.md"),
        ("", "rapport-{id}.md"),
        ("« — »", "rapport-{id}.md"),
    ],
)
def test_rapport_markdown_filename(app, client, title, expected):
    """DOD-2 et DOD-4 — nom tiré du titre, replié sur le numéro quand le titre ne donne rien."""
    report = make_report(title)

    response = client.get(
        f"/rapports/{report.id}.md",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert response.headers["content-disposition"] == f'attachment; filename="{expected.format(id=report.id)}"'


def test_rapport_markdown_keeps_the_report_text_untouched(app, client):
    """DOD-3 — le fichier contient le texte du rapport tel qu'il a été écrit, en-tête comprise."""
    content = "---\ndate: 2026-01-01\n---\n\n# Résumé\n\nAccents : é, è, ê, à, ç, ù."
    report = make_report("Rapport avec accents", content=content)

    response = client.get(
        f"/rapports/{report.id}.md",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert response.content.decode("utf-8") == content


def test_rapport_markdown_nonexistent_report_returns_404(app, client):
    """GET /rapports/<inexistant>.md renvoie 404."""
    response = client.get(
        "/rapports/99999.md",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert response.status_code == 404


def test_rapport_txt_redirects_to_markdown(app, client, report):
    """DOD-5 — les liens déjà partagés vers la « version exportable » mènent toujours au rapport."""
    response = client.get(
        f"/rapports/{report.id}.txt",
        headers={"X-Forwarded-Email": "test@example.com"},
        follow_redirects=False,
    )
    assert response.status_code == 301
    assert response.headers["location"] == f"/rapports/{report.id}.md"


def test_rapport_detail_view_has_download_button(app, client, report):
    """DOD-1 — la page du rapport porte le bouton « Télécharger en Markdown »."""
    response = client.get(
        f"/rapports/{report.id}",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert response.status_code == 200
    assert "Télécharger en Markdown".encode() in response.content
    assert f"/rapports/{report.id}.md".encode() in response.content


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
