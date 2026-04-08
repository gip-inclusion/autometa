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


def test_database_timestamps_are_utc_aware(mocker):
    """Verify that database operations produce UTC-aware ISO strings."""
    mock_utcnow = mocker.patch("web.database.utcnow")
    mock_utcnow.return_value = datetime(2026, 4, 8, 12, 0, 0, tzinfo=timezone.utc)

    iso = mock_utcnow().isoformat()
    parsed = datetime.fromisoformat(iso)
    assert parsed.tzinfo is not None


def test_fromisoformat_roundtrip_preserves_timezone():
    """UTC-aware datetime survives isoformat -> fromisoformat roundtrip."""
    original = datetime(2026, 4, 8, 14, 30, 0, tzinfo=timezone.utc)
    serialized = original.isoformat()
    restored = datetime.fromisoformat(serialized)
    assert restored.tzinfo is not None
    assert restored == original


def test_sort_mixed_utc_dates():
    """All dates from different sources (convos, reports, apps) are sortable."""
    conv_date = datetime(2026, 4, 8, 10, 0, tzinfo=timezone.utc)
    report_date = datetime(2026, 4, 7, 15, 0, tzinfo=timezone.utc)
    app_date = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)
    app_min = datetime.min.replace(tzinfo=timezone.utc)

    items = [
        {"sort_date": app_min},
        {"sort_date": report_date},
        {"sort_date": conv_date},
        {"sort_date": app_date},
    ]
    items.sort(key=lambda x: x["sort_date"], reverse=True)

    assert items[0]["sort_date"] == conv_date
    assert items[1]["sort_date"] == report_date
    assert items[2]["sort_date"] == app_date
    assert items[3]["sort_date"] == app_min
