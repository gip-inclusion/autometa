"""Tests for the Notion client (lib.notion): read, markdown conversion, publish endpoint, UI button."""

import pytest

SAMPLE_REPORT = """\
---
date: 2026-01-15
website: emplois
original_query: "Quels sont les événements les plus fréquents ?"
query_category: "Event analysis"
---

# Analyse des événements

## Contexte

Ce rapport analyse les **événements principaux** sur le site *Emplois*.

### Données clés

| Événement | Volume | Description |
|-----------|--------|-------------|
| **clic-metiers** | 84 316 | Filtrage par métiers |
| start_application | 63 094 | Début candidature |

### Parcours utilisateur

```mermaid
flowchart TD
    A["Recherche"] --> B["Filtrage"]
    B --> C["Candidature"]
```

### Implémentation

```python
def track_event(category, action, name):
    _paq.push(['trackEvent', category, action, name])
```

- Premier point avec `code inline`
- Deuxième point avec [un lien](https://example.com)

1. Étape numérotée une
2. Étape numérotée deux

---

Fin du rapport.
"""


@pytest.fixture
def report(app):
    from web.database import store

    return store.create_report(
        title="Analyse des événements",
        content=SAMPLE_REPORT,
        website="emplois",
        category="Event analysis",
        user_id="test@example.com",
    )


@pytest.fixture
def report_with_db_query(app):
    from web.database import store

    return store.create_report(
        title="Test Report",
        content=SAMPLE_REPORT,
        website="emplois",
        category="testing",
        original_query="Generate a report about events",
        user_id="test@example.com",
    )


def test_markdown_to_blocks_strips_yaml_frontmatter():
    from lib.notion import markdown_to_blocks

    blocks = markdown_to_blocks("---\ndate: 2026-01-01\n---\n\n# Title\n")
    types = [b["type"] for b in blocks]
    assert "paragraph" not in types or not any("date:" in str(b) for b in blocks)
    assert any(b["type"] == "heading_1" for b in blocks)


def test_markdown_to_blocks_headings():
    from lib.notion import markdown_to_blocks

    blocks = markdown_to_blocks("# H1\n\n## H2\n\n### H3\n")
    types = [b["type"] for b in blocks]
    assert types == ["heading_1", "heading_2", "heading_3"]


def test_markdown_to_blocks_paragraph_with_inline_formatting():
    from lib.notion import markdown_to_blocks

    blocks = markdown_to_blocks("This is **bold** and *italic* and `code`.\n")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "paragraph"
    rich = blocks[0]["paragraph"]["rich_text"]
    annotations = {r["text"]["content"]: r["annotations"] for r in rich}
    assert annotations["bold"]["bold"] is True
    assert annotations["italic"]["italic"] is True
    assert annotations["code"]["code"] is True


def test_markdown_to_blocks_link_parsing():
    from lib.notion import markdown_to_blocks

    blocks = markdown_to_blocks("See [example](https://example.com) here.\n")
    rich = blocks[0]["paragraph"]["rich_text"]
    link_obj = next(r for r in rich if r["text"].get("link"))
    assert link_obj["text"]["link"]["url"] == "https://example.com"
    assert link_obj["text"]["content"] == "example"


def test_markdown_to_blocks_code_block_with_language():
    from lib.notion import markdown_to_blocks

    blocks = markdown_to_blocks("```python\nprint('hello')\n```\n")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "code"
    assert blocks[0]["code"]["language"] == "python"
    assert blocks[0]["code"]["rich_text"][0]["text"]["content"] == "print('hello')"


def test_markdown_to_blocks_mermaid_block():
    from lib.notion import markdown_to_blocks

    blocks = markdown_to_blocks("```mermaid\nflowchart TD\n    A --> B\n```\n")
    assert blocks[0]["type"] == "code"
    assert blocks[0]["code"]["language"] == "mermaid"


def test_markdown_to_blocks_table():
    from lib.notion import markdown_to_blocks

    md = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n"
    blocks = markdown_to_blocks(md)
    assert len(blocks) == 1
    table = blocks[0]
    assert table["type"] == "table"
    assert table["table"]["table_width"] == 2
    assert table["table"]["has_column_header"] is True
    rows = table["table"]["children"]
    assert len(rows) == 3
    first_cell = rows[0]["table_row"]["cells"][0][0]["text"]["content"]
    assert first_cell.strip() == "A"


def test_markdown_to_blocks_bullet_list():
    from lib.notion import markdown_to_blocks

    blocks = markdown_to_blocks("- one\n- two\n")
    assert len(blocks) == 2
    assert all(b["type"] == "bulleted_list_item" for b in blocks)


def test_markdown_to_blocks_numbered_list():
    from lib.notion import markdown_to_blocks

    blocks = markdown_to_blocks("1. first\n2. second\n")
    assert len(blocks) == 2
    assert all(b["type"] == "numbered_list_item" for b in blocks)


def test_markdown_to_blocks_divider():
    from lib.notion import markdown_to_blocks

    blocks = markdown_to_blocks("text\n\n---\n\nmore text\n")
    types = [b["type"] for b in blocks]
    assert "divider" in types


def test_markdown_to_blocks_full_report_block_count():
    """The sample report should produce a reasonable number of blocks."""
    from lib.notion import markdown_to_blocks

    blocks = markdown_to_blocks(SAMPLE_REPORT)
    assert len(blocks) > 10
    types = {b["type"] for b in blocks}
    assert types >= {
        "heading_1",
        "heading_2",
        "heading_3",
        "paragraph",
        "table",
        "code",
        "bulleted_list_item",
        "numbered_list_item",
        "divider",
    }


def test_markdown_to_blocks_code_block_truncated_at_2000():
    from lib.notion import markdown_to_blocks

    long_code = "x" * 3000
    blocks = markdown_to_blocks(f"```python\n{long_code}\n```\n")
    content = blocks[0]["code"]["rich_text"][0]["text"]["content"]
    assert len(content) <= 2000


def test_frontmatter_extraction_query_overrides_db_field(mocker):
    from lib.notion import publish_report

    mocker.patch("lib.notion.is_configured", return_value=True)
    mock_req = mocker.patch("lib.notion.notion_request")
    mock_req.return_value = {"id": "abc", "url": "https://notion.so/page"}
    publish_report(
        title="Test",
        content=SAMPLE_REPORT,
        original_query="Generate a report about something",
    )
    call_args = mock_req.call_args_list[0]
    payload = call_args[0][2]
    query_text = payload["properties"]["Requête initiale"]["rich_text"][0]["text"]["content"]
    assert query_text == "Quels sont les événements les plus fréquents ?"


def test_frontmatter_extraction_date_overrides_argument(mocker):
    from lib.notion import publish_report

    mocker.patch("lib.notion.is_configured", return_value=True)
    mock_req = mocker.patch("lib.notion.notion_request")
    mock_req.return_value = {"id": "abc", "url": "https://notion.so/page"}
    publish_report(
        title="Test",
        content=SAMPLE_REPORT,
        date="1999-01-01",
    )
    call_args = mock_req.call_args_list[0]
    payload = call_args[0][2]
    assert payload["properties"]["Date de publication"]["date"]["start"] == "2026-01-15"


def test_frontmatter_extraction_db_field_used_when_no_frontmatter(mocker):
    from lib.notion import publish_report

    mocker.patch("lib.notion.is_configured", return_value=True)
    mock_req = mocker.patch("lib.notion.notion_request")
    mock_req.return_value = {"id": "abc", "url": "https://notion.so/page"}
    content_no_fm = "# Just a heading\n\nSome text.\n"
    publish_report(
        title="Test",
        content=content_no_fm,
        original_query="fallback query",
        date="2026-06-01",
    )
    call_args = mock_req.call_args_list[0]
    payload = call_args[0][2]
    assert payload["properties"]["Requête initiale"]["rich_text"][0]["text"]["content"] == "fallback query"
    assert payload["properties"]["Date de publication"]["date"]["start"] == "2026-06-01"


def test_publish_notion_endpoint_returns_503_when_not_configured(mocker, app, client, report):
    mocker.patch("lib.notion.is_configured", return_value=False)
    resp = client.post(
        f"/api/reports/{report.id}/publish-notion",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert resp.status_code == 503


def test_publish_notion_endpoint_returns_404_for_missing_report(mocker, app, client):
    mocker.patch("lib.notion.is_configured", return_value=True)
    resp = client.post(
        "/api/reports/99999/publish-notion",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert resp.status_code == 404


def test_publish_notion_endpoint_publishes_and_stores_url(mocker, app, client, report):
    mocker.patch("lib.notion.is_configured", return_value=True)
    mock_publish = mocker.patch("lib.notion.publish_report")
    mock_publish.return_value = ("page-id-123", "https://notion.so/My-Page-123")
    resp = client.post(
        f"/api/reports/{report.id}/publish-notion",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"] == "https://notion.so/My-Page-123"

    mock_publish.reset_mock()
    resp2 = client.post(
        f"/api/reports/{report.id}/publish-notion",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["url"] == "https://notion.so/My-Page-123"
    mock_publish.assert_not_called()


def test_publish_notion_endpoint_returns_500_on_error(mocker, app, client, report):
    mocker.patch("lib.notion.is_configured", return_value=True)
    mocker.patch("lib.notion.publish_report", side_effect=Exception("timeout"))
    resp = client.post(
        f"/api/reports/{report.id}/publish-notion",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert resp.status_code == 500
    assert resp.json()["error"] == "Failed to publish to Notion"


def test_notion_button_shows_export_button_when_no_url(app, client, report):
    resp = client.get(
        f"/rapports/{report.id}",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert resp.status_code == 200
    assert b'id="notionBtn" data-report-id=' in resp.content
    assert b'href="https://notion.so' not in resp.content


@pytest.mark.parametrize(
    "url",
    [
        "https://www.notion.so/ws/1455f321b60480f68fb4fbab8ad1a6e9?v=1535f321b6048065ab68000cb9523310",
        "https://app.notion.com/p/gip-inclusion/1455f321b60480f68fb4fbab8ad1a6e9",
        "https://www.notion.so/1455f321-b604-80f6-8fb4-fbab8ad1a6e9",
        "https://www.notion.so/Page-Title-1455f321b60480f68fb4fbab8ad1a6e9#some-block",
    ],
)
def test_db_id_from_url_ignores_view_id(url):
    from lib import notion

    assert notion.db_id_from_url(url) == "1455f321-b604-80f6-8fb4-fbab8ad1a6e9"


def test_db_id_from_url_raises_without_id():
    from lib import notion

    with pytest.raises(ValueError, match="No Notion id"):
        notion.db_id_from_url("https://www.notion.so/no-id-here")


def test_query_database_paginates(mocker):
    from lib import notion

    req = mocker.patch(
        "lib.notion.notion_request",
        side_effect=[
            {"results": [{"id": "a"}], "has_more": True, "next_cursor": "c1"},
            {"results": [{"id": "b"}], "has_more": False},
        ],
    )
    result = notion.query_database("db1")

    assert [p["id"] for p in result] == ["a", "b"]
    assert req.call_count == 2
    assert req.call_args_list[0][0][1] == "databases/db1/query"
    assert req.call_args_list[1][0][2]["start_cursor"] == "c1"


def test_notion_request_retries_on_429(mocker):
    from lib import notion

    r429 = mocker.Mock(status_code=429, headers={"Retry-After": "0"})
    r200 = mocker.Mock(status_code=200)
    r200.json.return_value = {"ok": True}
    req = mocker.patch("lib.notion.httpx.request", side_effect=[r429, r200])
    sleep = mocker.patch("lib.notion.time.sleep")

    assert notion.notion_request("GET", "users/me") == {"ok": True}
    assert req.call_count == 2
    sleep.assert_called_once_with(0.0)


def test_notion_request_raises_after_persistent_429(mocker):
    from lib import notion

    r429 = mocker.Mock(status_code=429, headers={"Retry-After": "0"})
    req = mocker.patch("lib.notion.httpx.request", return_value=r429)
    mocker.patch("lib.notion.time.sleep")

    with pytest.raises(RuntimeError, match="rate-limited"):
        notion.notion_request("GET", "users/me")
    assert req.call_count == 4


def test_get_block_children_recurses_into_nested(mocker):
    from lib import notion

    req = mocker.patch(
        "lib.notion.notion_request",
        side_effect=[
            {"results": [{"id": "p", "type": "paragraph", "has_children": True}], "has_more": False},
            {"results": [{"id": "c", "type": "paragraph", "has_children": False}], "has_more": False},
        ],
    )
    blocks = notion.get_block_children("root")

    assert [b["id"] for b in blocks] == ["p", "c"]
    assert req.call_count == 2


def test_extract_page_properties_maps_types():
    from lib import notion

    page = {
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "Hello"}]},
            "Notes": {"type": "rich_text", "rich_text": [{"plain_text": "abc"}]},
            "Cat": {"type": "select", "select": {"name": "X"}},
            "Tags": {"type": "multi_select", "multi_select": [{"name": "a"}, {"name": "b"}]},
            "When": {"type": "date", "date": {"start": "2026-01-01"}},
            "Empty": {"type": "select", "select": None},
            "Rel": {"type": "relation", "relation": [{"id": "r1"}]},
            "Score": {"type": "formula", "formula": {"type": "number", "number": 42}},
            "Other": {"type": "checkbox", "checkbox": True},
        }
    }
    assert notion.extract_page_properties(page) == {
        "Name": "Hello",
        "Notes": "abc",
        "Cat": "X",
        "Tags": ["a", "b"],
        "When": "2026-01-01",
        "Empty": None,
        "Rel": ["r1"],
        "Score": 42,
        "Other": None,
    }


def test_extract_page_title():
    from lib import notion

    page = {
        "properties": {
            "Tags": {"type": "multi_select", "multi_select": []},
            "Name": {"type": "title", "title": [{"plain_text": "My page"}]},
        }
    }
    assert notion.extract_page_title(page) == "My page"


@pytest.mark.parametrize(
    ("block", "expected"),
    [
        ({"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "hi"}]}}, "hi"),
        ({"type": "child_page", "child_page": {"title": "Page"}}, "Page"),
        ({"type": "child_database", "child_database": {"title": "DB"}}, "DB"),
        ({"type": "caption", "caption": {"text": [{"plain_text": "cap"}]}}, "cap"),
        ({"type": "divider", "divider": {}}, ""),
    ],
)
def test_extract_block_text(block, expected):
    from lib import notion

    assert notion.extract_block_text(block) == expected


def test_notion_button_shows_link_after_publish(mocker, app, client, report):
    mocker.patch("lib.notion.is_configured", return_value=True)
    mock_publish = mocker.patch("lib.notion.publish_report")
    mock_publish.return_value = ("page-id", "https://notion.so/Page-123")
    client.post(
        f"/api/reports/{report.id}/publish-notion",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    resp = client.get(
        f"/rapports/{report.id}",
        headers={"X-Forwarded-Email": "test@example.com"},
    )
    assert resp.status_code == 200
    assert "Lien Notion".encode() in resp.content
    assert b"https://notion.so/Page-123" in resp.content
