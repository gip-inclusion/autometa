"""Tests for web.routes.html time-display helpers (timezone localization)."""

from datetime import datetime, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

from web.routes.html import _group_items_by_date, format_relative_date

PARIS = ZoneInfo("Europe/Paris")


class TestFormatRelativeDateTimezone:
    """format_relative_date should display times in Europe/Paris, not UTC."""

    def test_today_shows_paris_time(self):
        """A 14:00 UTC event today should show 15:00 in winter (CET=UTC+1)."""
        # Fix "now" to a known winter datetime in Paris
        # 2026-01-15 10:00 UTC = 11:00 CET
        fake_now = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
        with patch("web.routes.html._now_local", return_value=fake_now.astimezone(PARIS)):
            # Event at 09:30 UTC = 10:30 CET — same day
            dt = datetime(2026, 1, 15, 9, 30)
            result = format_relative_date(dt)
            assert result == "10:30"

    def test_utc_evening_becomes_next_day_in_paris(self):
        """23:30 UTC on Monday = 00:30 Tuesday CET → should show 'mardi 00:30'."""
        # "now" is Tuesday 01:00 CET = 00:00 UTC
        fake_now = datetime(2026, 1, 13, 0, 0, tzinfo=timezone.utc)
        with patch("web.routes.html._now_local", return_value=fake_now.astimezone(PARIS)):
            # Event at Monday 23:30 UTC = Tuesday 00:30 CET
            dt = datetime(2026, 1, 12, 23, 30)
            result = format_relative_date(dt)
            # Tuesday 00:30 is "today" relative to now (Tuesday 01:00 CET)
            assert result == "00:30"

    def test_yesterday_paris_time(self):
        """An event from yesterday shows 'hier' with Paris time."""
        # Now is Wednesday 2026-01-14 12:00 CET
        fake_now = datetime(2026, 1, 14, 11, 0, tzinfo=timezone.utc)
        with patch("web.routes.html._now_local", return_value=fake_now.astimezone(PARIS)):
            # Event at Tuesday 2026-01-13 15:00 UTC = 16:00 CET (yesterday)
            dt = datetime(2026, 1, 13, 15, 0)
            result = format_relative_date(dt)
            assert result == "hier, 16:00"

    def test_summer_time_offset(self):
        """In summer (CEST=UTC+2), times shift by 2 hours."""
        # 2026-07-15 10:00 UTC = 12:00 CEST
        fake_now = datetime(2026, 7, 15, 10, 0, tzinfo=timezone.utc)
        with patch("web.routes.html._now_local", return_value=fake_now.astimezone(PARIS)):
            # Event at 08:00 UTC = 10:00 CEST
            dt = datetime(2026, 7, 15, 8, 0)
            result = format_relative_date(dt)
            assert result == "10:00"

    def test_weekday_shows_paris_time(self):
        """Events earlier this week show day name with Paris time."""
        # Now is Thursday 2026-01-15 12:00 CET
        fake_now = datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc)
        with patch("web.routes.html._now_local", return_value=fake_now.astimezone(PARIS)):
            # Event on Tuesday 2026-01-13 14:00 UTC = 15:00 CET
            dt = datetime(2026, 1, 13, 14, 0)
            result = format_relative_date(dt)
            assert result == "mardi 15:00"

    def test_old_date_shows_paris_time(self):
        """Old events show full date with Paris time."""
        fake_now = datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc)
        with patch("web.routes.html._now_local", return_value=fake_now.astimezone(PARIS)):
            # Event on 2025-12-25 20:00 UTC = 21:00 CET
            dt = datetime(2025, 12, 25, 20, 0)
            result = format_relative_date(dt)
            assert result == "25/12/2025 à 21:00"


class TestGroupItemsByDateTimezone:
    """_group_items_by_date should use Paris time for grouping."""

    def test_late_utc_grouped_as_next_day(self):
        """23:30 UTC = 00:30 CET next day → grouped in next day's bucket."""
        # Now is Tuesday 2026-01-13 01:00 CET (00:00 UTC)
        fake_now = datetime(2026, 1, 13, 0, 0, tzinfo=timezone.utc)
        with patch("web.routes.html._now_local", return_value=fake_now.astimezone(PARIS)):
            items = [
                {"sort_date": datetime(2026, 1, 12, 23, 30)},  # Mon 23:30 UTC = Tue 00:30 CET
            ]
            groups = _group_items_by_date(items)
            # Should be in "aujourd'hui" (Tuesday), not "hier" (Monday)
            assert "aujourd'hui" in groups
            assert len(groups["aujourd'hui"]) == 1
