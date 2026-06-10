"""Tests for shared template helpers."""

import pytest

from web.deps import markdown_filter


@pytest.mark.parametrize(
    "payload",
    [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "<a href='javascript:alert(1)'>x</a>",
        "<iframe src='evil'></iframe>",
    ],
)
def test_markdown_filter_strips_active_content(payload):
    out = str(markdown_filter(payload))
    assert "<script" not in out
    assert "onerror" not in out
    assert "javascript:" not in out
    assert "<iframe" not in out


def test_markdown_filter_preserves_formatting():
    out = str(markdown_filter("# Titre\n\n**gras**\n\n| a | b |\n|---|---|\n| 1 | 2 |"))
    assert "<h1>Titre</h1>" in out
    assert "<strong>gras</strong>" in out
    assert "<table>" in out


def test_markdown_filter_handles_none():
    assert str(markdown_filter(None)) == ""
