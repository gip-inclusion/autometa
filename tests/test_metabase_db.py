"""Tests for Metabase cards inventory (PostgreSQL backend)."""

import json

import pytest
from sqlalchemy import text

from skills.metabase_query.scripts.cards_db import TOPICS, Card, CardsDB
from web.db import get_db
from web.schema import init_db


@pytest.fixture
def db():
    init_db()
    instance = "test"
    with get_db() as session:
        session.execute(text("DELETE FROM metabase_cards WHERE instance = :inst"), {"inst": instance})
        session.execute(text("DELETE FROM metabase_dashboards WHERE instance = :inst"), {"inst": instance})
    yield CardsDB(instance=instance)
    with get_db() as session:
        session.execute(text("DELETE FROM metabase_cards WHERE instance = :inst"), {"inst": instance})
        session.execute(text("DELETE FROM metabase_dashboards WHERE instance = :inst"), {"inst": instance})


@pytest.fixture
def populated_db(db):
    with get_db() as session:
        for card_id, name, desc, topic, sql, tables, dash_id in [
            (
                1,
                "File active count",
                "Count of candidates in file active",
                "file-active",
                "SELECT COUNT(*) FROM candidats WHERE status = 'active'",
                ["candidats"],
                408,
            ),
            (
                2,
                "Candidatures by region",
                "Breakdown of applications by region",
                "candidatures",
                "SELECT region, COUNT(*) FROM candidatures GROUP BY region",
                ["candidatures"],
                408,
            ),
            (
                3,
                "Gender demographics",
                None,
                "demographie",
                "SELECT gender, COUNT(*) FROM candidats GROUP BY gender",
                ["candidats"],
                267,
            ),
        ]:
            session.execute(
                text("""INSERT INTO metabase_cards (id, instance, name, description, topic, sql_query, tables_json, dashboard_id)
                   VALUES (:id, :inst, :name, :desc, :topic, :sql, :tables, :did)"""),
                {
                    "id": card_id,
                    "inst": db.instance,
                    "name": name,
                    "desc": desc,
                    "topic": topic,
                    "sql": sql,
                    "tables": json.dumps(tables),
                    "did": dash_id,
                },
            )
    return db


def test_get_card(populated_db):
    card = populated_db.get(1)
    assert card is not None
    assert card.id == 1
    assert card.name == "File active count"
    assert card.topic == "file-active"
    assert card.tables_referenced == ["candidats"]


def test_get_nonexistent(populated_db):
    assert populated_db.get(99999) is None


def test_all(populated_db):
    cards = populated_db.all()
    assert len(cards) == 3
    assert all(isinstance(c, Card) for c in cards)


def test_count(populated_db):
    assert populated_db.count() == 3


def test_by_topic(populated_db):
    cards = populated_db.by_topic("file-active")
    assert len(cards) == 1
    assert cards[0].id == 1


def test_by_topic_empty(populated_db):
    assert populated_db.by_topic("nonexistent") == []


def test_search(populated_db):
    cards = populated_db.search("file active")
    assert len(cards) >= 1
    assert any(c.id == 1 for c in cards)


def test_search_by_sql(populated_db):
    cards = populated_db.search("region")
    assert len(cards) >= 1
    assert any(c.id == 2 for c in cards)


def test_by_table(populated_db):
    cards = populated_db.by_table("candidats")
    assert len(cards) == 2
    assert {c.id for c in cards} == {1, 3}


def test_by_dashboard(populated_db):
    cards = populated_db.by_dashboard(408)
    assert len(cards) == 2


def test_topics_summary(populated_db):
    summary = populated_db.topics_summary()
    assert summary["file-active"] == 1
    assert summary["candidatures"] == 1
    assert summary["demographie"] == 1


def test_topics_defined():
    assert len(TOPICS) > 0
    for topic in ["file-active", "candidatures", "demographie"]:
        assert topic in TOPICS
