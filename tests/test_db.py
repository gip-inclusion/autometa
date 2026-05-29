"""Tests for web/db.py — SQLAlchemy slow-query listener."""

import logging

from sqlalchemy import text


def test_slow_query_listener_logs_above_threshold(mocker, caplog):
    from web.db import get_engine

    engine = get_engine()
    mocker.patch("web.db.SLOW_QUERY_THRESHOLD_MS", 0)

    with caplog.at_level(logging.INFO, logger="web.db"):
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    matches = [r for r in caplog.records if r.message == "db.slow_query"]
    assert len(matches) >= 1
    record = matches[0]
    assert getattr(record, "db.operation") == "SELECT"
    assert getattr(record, "db.duration") >= 0


def test_slow_query_listener_skips_below_threshold(mocker, caplog):
    from web.db import get_engine

    engine = get_engine()
    mocker.patch("web.db.SLOW_QUERY_THRESHOLD_MS", 10_000)

    with caplog.at_level(logging.INFO, logger="web.db"):
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    assert not any(r.message == "db.slow_query" for r in caplog.records)
