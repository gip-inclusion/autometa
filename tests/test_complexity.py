"""Tests for web/complexity.py — détection de conversations complexes."""

import json

import pytest

from web import complexity
from web.database import Message


def _user():
    return Message(type="user", content="question")


def _data_query(category="API: Metabase", sql=""):
    return Message(type="tool_use", content=json.dumps({"tool": "q", "input": {"sql": sql}, "category": category}))


def _read():
    return Message(type="tool_use", content=json.dumps({"tool": "Read", "input": {}, "category": "Read: code"}))


def _sources(*pairs):
    api_calls = [{"source": s, "instance": i} for s, i in pairs]
    return Message(type="tool_result", content=json.dumps({"output": "x", "api_calls": api_calls}))


def _assistant(text):
    return Message(type="assistant", content=text)


def test_simple_conversation_is_not_complex():
    messages = [_user(), _data_query(), _data_query(), _user()]
    assert complexity.evaluate(messages) == []


@pytest.mark.parametrize(
    "messages, indicator",
    [
        ([_data_query() for _ in range(51)], "requêtes"),
        ([_user() for _ in range(41)], "tours"),
        ([_sources(("matomo", "a"), ("metabase", "b"), ("metabase", "c"), ("metabase", "d"))], "sources"),
        ([_data_query(sql="SELECT * FROM a JOIN b ON 1 JOIN c ON 1 JOIN d ON 1 JOIN e ON 1")], "jointure"),
    ],
)
def test_each_indicator_triggers(messages, indicator):
    reasons = complexity.evaluate(messages)
    assert any(r.startswith(indicator) for r in reasons)


@pytest.mark.parametrize(
    "messages",
    [
        [_data_query() for _ in range(50)],
        [_user() for _ in range(40)],
        [_sources(("matomo", "a"), ("metabase", "b"), ("metabase", "c"))],
        [_data_query(sql="SELECT * FROM a JOIN b ON 1 JOIN c ON 1 JOIN d ON 1")],
    ],
)
def test_just_below_threshold_is_not_complex(messages):
    assert complexity.evaluate(messages) == []


def test_non_data_tool_calls_do_not_count_as_queries():
    assert complexity.evaluate([_read() for _ in range(60)]) == []


def test_already_alerted_detects_previous_alert():
    messages = [_user(), _assistant(complexity.ALERT_MESSAGE)]
    assert complexity.already_alerted(messages)


def test_already_alerted_false_without_alert():
    assert not complexity.already_alerted([_user(), _assistant("réponse normale")])


@pytest.mark.parametrize(
    "sql, expected",
    [
        ("SELECT 1", 0),
        ("SELECT * FROM candidatures", 1),
        ("SELECT * FROM a JOIN b ON a.id = b.id", 2),
        ("SELECT * FROM schema.tbl JOIN other ON 1", 2),
    ],
)
def test_table_count(sql, expected):
    assert complexity._table_count(sql) == expected
