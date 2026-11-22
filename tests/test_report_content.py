"""Rendu HTML d'un rapport : l'agent en écrit le texte, la page n'en garde rien d'actif."""

import pytest

from web.routes.reports import render_report_content


@pytest.mark.parametrize(
    ("payload", "forbidden"),
    [
        ("<script>alert(1)</script>", "<script"),
        ("<img src=x onerror=alert(1)>", "onerror"),
        ("<a href='javascript:alert(1)'>x</a>", "javascript:"),
        ("<iframe src='https://example.org'></iframe>", "<iframe"),
        ("<div style='position: fixed'>x</div>", "style="),
    ],
)
def test_a_report_keeps_none_of_its_active_html(payload, forbidden):
    _, html = render_report_content(f"# Titre\n\n{payload}\n")
    assert forbidden not in html


def test_a_report_keeps_its_tables_diagrams_and_anchors():
    _, html = render_report_content(
        "# Titre\n\n[vers le titre](#titre)\n\n| a |\n|---|\n| 1<br>2 |\n\n```mermaid\ngraph TD; A-->B\n```\n"
    )
    assert '<h1 id="titre">' in html
    assert '<a href="#titre"' in html
    assert '<table class="table table-sm table-striped">' in html
    assert "1<br>2" in html
    assert '<code class="language-mermaid">' in html
