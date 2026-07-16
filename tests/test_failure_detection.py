"""Tests for lib/failure_detection.py — persistence into the dashboard_storage schema."""

import pytest
from sqlalchemy import delete, select

from lib import failure_detection
from web.db import get_engine


@pytest.mark.integration
def test_record_failure_roundtrip():
    failure_detection.ensure_schema()
    failure_detection.record_failure(
        "conv-roundtrip",
        "Ma conversation",
        "désolé",
        "je suis désolé, erreur.",
        "http://x/explorations/conv-roundtrip",
        "user-42",
    )
    table = failure_detection.conversation_failures
    try:
        with get_engine().begin() as conn:
            row = conn.execute(
                select(table).where(table.c.conversation_id == "conv-roundtrip").order_by(table.c.id.desc())
            ).first()
        assert row.conversation_id == "conv-roundtrip"
        assert row.user_id == "user-42"
        assert row.marker == "désolé"
        assert row.snippet == "je suis désolé, erreur."
        assert row.url == "http://x/explorations/conv-roundtrip"
        assert row.detected_at is not None
    finally:
        with get_engine().begin() as conn:
            conn.execute(delete(table).where(table.c.conversation_id == "conv-roundtrip"))
