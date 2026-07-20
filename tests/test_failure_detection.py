"""Tests for lib/failure_detection.py — persistence into the dashboard_storage schema."""

from datetime import timezone

import pytest
from sqlalchemy import delete, inspect, select

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


@pytest.mark.integration
def test_conversation_id_is_indexed():
    failure_detection.ensure_schema()
    with get_engine().connect() as conn:
        indexed = inspect(conn).get_indexes("conversation_failures", schema=failure_detection.SCHEMA)
    assert any(ix["column_names"] == ["conversation_id"] for ix in indexed)


def test_ensure_schema_creates_schema_then_tables(mocker):
    engine = mocker.MagicMock()
    mocker.patch("lib.failure_detection.get_engine", return_value=engine)
    create_all = mocker.patch("sqlalchemy.MetaData.create_all")

    failure_detection.ensure_schema()

    statement = engine.begin.return_value.__enter__.return_value.execute.call_args[0][0]
    assert str(statement) == f"CREATE SCHEMA IF NOT EXISTS {failure_detection.SCHEMA}"
    create_all.assert_called_once_with(engine)


def test_record_failure_inserts_row_with_utc_timestamp(mocker):
    engine = mocker.MagicMock()
    mocker.patch("lib.failure_detection.get_engine", return_value=engine)

    failure_detection.record_failure("conv-1", "Ma conv", "désolé", "boom", "http://x", "user-9")

    statement = engine.begin.return_value.__enter__.return_value.execute.call_args[0][0]
    assert statement.table is failure_detection.conversation_failures
    params = statement.compile().params
    assert params["conversation_id"] == "conv-1"
    assert params["user_id"] == "user-9"
    assert params["marker"] == "désolé"
    assert params["detected_at"].tzinfo is timezone.utc


def test_record_failure_defaults_user_id_to_none(mocker):
    engine = mocker.MagicMock()
    mocker.patch("lib.failure_detection.get_engine", return_value=engine)

    failure_detection.record_failure("conv-1", "Ma conv", "désolé", "boom", "http://x")

    statement = engine.begin.return_value.__enter__.return_value.execute.call_args[0][0]
    assert statement.compile().params["user_id"] is None
