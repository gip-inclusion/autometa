"""Tests for lib/dashboards.detect_api_flags."""

from pathlib import Path

import pytest

from lib.dashboards import detect_api_flags


def _make_slug_dir(tmp_path: Path, files: dict[str, str]) -> Path:
    slug_dir = tmp_path / "tdb"
    slug_dir.mkdir()
    for name, content in files.items():
        (slug_dir / name).write_text(content)
    return slug_dir


@pytest.mark.parametrize(
    ("files", "metadata", "expected"),
    [
        ({}, {}, (False, False)),
        ({"app.js": "fetch('/api/query', {body: 'SELECT * FROM foo'})"}, {}, (True, False)),
        ({"app.js": "fetch('/api/query', {body: 'INSERT INTO foo VALUES (1)'})"}, {}, (True, True)),
        ({"app.js": "fetch('/api/query', {body: 'DELETE FROM foo WHERE id=1'})"}, {}, (True, True)),
        ({"app.js": "fetch('/api/query', {body: 'UPDATE foo SET x=1'})"}, {}, (True, True)),
        ({"app.js": "fetch('/api/query', {body: 'CREATE TABLE foo (id INT)'})"}, {}, (True, True)),
        ({"app.js": "delete charts[id]; document.getElementById('dialog-delete')"}, {}, (False, False)),
        (
            {"app.js": "fetch('/api/query', {body: 'SELECT 1'}); delete charts[id]"},
            {},
            (True, False),
        ),
        ({"index.html": "<script>fetch('/api/query')</script>"}, {}, (True, False)),
        ({}, {"has_api_access": True, "has_persistence": False}, (True, False)),
        ({}, {"has_api_access": True, "has_persistence": True}, (True, True)),
        (
            {"app.js": "fetch('/api/query')"},
            {"has_api_access": False, "has_persistence": False},
            (False, False),
        ),
        (
            {"app.js": "fetch('/api/query', {body: 'INSERT INTO foo VALUES (1)'})"},
            {"has_api_access": True},
            (True, True),
        ),
        ({"app.js": "INSERT INTO foo VALUES (1)"}, {}, (False, False)),
        ({"app.js": "fetch('/api/query', {body: 'insert into foo values (1)'})"}, {}, (True, True)),
        ({"styles.css": "body { color: red; }", "app.json": "{}"}, {}, (False, False)),
    ],
    ids=[
        "empty-dir",
        "select-only",
        "insert-into",
        "delete-from",
        "update-set",
        "create-table",
        "js-delete-no-api",
        "js-delete-with-api",
        "html-fetch",
        "frontmatter-api-true",
        "frontmatter-both-true",
        "frontmatter-overrides-heuristic",
        "frontmatter-partial-api-true",
        "insert-without-api",
        "lowercase-sql",
        "ignored-file-types",
    ],
)
def test_detect_api_flags(tmp_path, files, metadata, expected):
    slug_dir = _make_slug_dir(tmp_path, files)
    assert detect_api_flags(slug_dir, metadata) == expected


def test_detect_api_flags_handles_binary_in_html(tmp_path):
    slug_dir = tmp_path / "tdb"
    slug_dir.mkdir()
    (slug_dir / "blob.html").write_bytes(b"\xff\xfe\x00binary\x00")
    (slug_dir / "app.js").write_text("fetch('/api/query')")
    assert detect_api_flags(slug_dir, {}) == (True, False)


def test_detect_api_flags_scans_subdirectories(tmp_path):
    slug_dir = tmp_path / "tdb"
    nested = slug_dir / "vendor"
    nested.mkdir(parents=True)
    (nested / "lib.js").write_text("fetch('/api/query', {body: 'INSERT INTO foo VALUES (1)'})")
    assert detect_api_flags(slug_dir, {}) == (True, True)
