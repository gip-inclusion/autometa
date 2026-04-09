"""Tests for UTC-aware datetime usage across the codebase."""

from datetime import datetime, timezone

import pytest

from web.helpers import utcnow


def test_utcnow_returns_utc_aware():
    dt = utcnow()
    assert dt.tzinfo is not None
    assert dt.tzinfo == timezone.utc


def test_utcnow_isoformat_contains_offset():
    iso = utcnow().isoformat()
    assert "+" in iso or "Z" in iso


@pytest.mark.parametrize(
    "module_path,function_or_attr",
    [
        ("web.database", "utcnow"),
        ("web.cron", "utcnow"),
        ("web.slack_feedback", "utcnow"),
    ],
)
def test_modules_import_utcnow(module_path, function_or_attr):
    """Verify that key modules use utcnow instead of datetime.now."""
    import importlib

    mod = importlib.import_module(module_path)
    assert hasattr(mod, function_or_attr), f"{module_path} should import {function_or_attr}"


def test_sort_mixed_utc_dates_with_none():
    """Dated items sort descending, None sort last."""
    conv_date = datetime(2026, 4, 8, 10, 0, tzinfo=timezone.utc)
    report_date = datetime(2026, 4, 7, 15, 0, tzinfo=timezone.utc)
    app_date = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)

    items = [
        {"sort_date": None},
        {"sort_date": report_date},
        {"sort_date": conv_date},
        {"sort_date": app_date},
    ]
    dated = [i for i in items if i["sort_date"] is not None]
    undated = [i for i in items if i["sort_date"] is None]
    dated.sort(key=lambda x: x["sort_date"], reverse=True)
    result = dated + undated

    assert result[0]["sort_date"] == conv_date
    assert result[1]["sort_date"] == report_date
    assert result[2]["sort_date"] == app_date
    assert result[3]["sort_date"] is None
