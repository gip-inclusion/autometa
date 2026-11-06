"""Les requêtes de l'audit, exécutées contre une vraie base : bornes, fenêtres, contexte, pagination."""

import re
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from tests.conftest import truncate_all_tables
from web import audit
from web.db import get_db
from web.models import Conversation, Message

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

C1, C2, FORK = (
    "11111111-0000-0000-0000-000000000000",
    "22222222-0000-0000-0000-000000000000",
    "33333333-0000-0000-0000-000000000000",
)


def at(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute, tzinfo=UTC)


@pytest.fixture(autouse=True)
def week():
    """Deux conversations et un fork créé le 10 qui recopie, avec un id récent, un message du 9. Les conversations sont
    insérées dans le désordre : sans tri, la base les rendrait dans l'ordre d'insertion."""
    truncate_all_tables()
    with get_db() as session:
        session.add_all([
            Conversation(id=FORK, user_id="b@x.fr", forked_from=C1, created_at=at(10, 12), updated_at=at(10, 12)),
            Conversation(id=C2, user_id="b@x.fr", created_at=at(1, 0), updated_at=at(1, 0)),
            Conversation(id=C1, user_id="a@x.fr", created_at=at(1, 0), updated_at=at(1, 0)),
        ])
        session.flush()
        session.add_all([
            Message(id=id_, conversation_id=conv, type=type_, role=type_, content=f"m{id_}", timestamp=ts)
            for id_, conv, type_, ts in [
                (10, C1, "user", at(9, 9)),
                (11, C1, "assistant", at(9, 9, 1)),
                (12, C1, "tool_use", at(9, 9, 2)),
                (20, C1, "user", at(10, 9)),
                (21, C2, "tool_result", at(10, 10)),
                (30, FORK, "user", at(9, 9)),
                (31, FORK, "user", at(10, 13)),
                (40, C2, "user", at(11, 8)),
            ]
        ])
    yield
    truncate_all_tables()


def run(sql, **params):
    """Une requête Metabase jouée en SQL lié : `{{x}}::type` devient `CAST(:x AS type)`, `{{x}}` devient `:x`."""
    sql = re.sub(r"\{\{(\w+)\}\}::(\w+)", r"CAST(:\1 AS \2)", sql)
    with get_db() as session:
        return [dict(row._mapping) for row in session.execute(text(re.sub(r"\{\{(\w+)\}\}", r":\1", sql)), params)]


@pytest.mark.parametrize(
    ("moment", "bound"),
    [
        # Minuit à Paris le 10 : le premier message du jour est le 20, pas le 30 recopié par le fork.
        (audit.day_start(datetime(2026, 10, 10).date()), 19),
        ("2026-10-11T00:00:00+02:00", 39),
        ("2030-01-01T00:00:00+00:00", 40),
    ],
)
def test_a_bound_is_the_last_id_before_the_first_message_from_that_moment(moment, bound):
    assert run(audit.BOUND_SQL, at=moment) == [{"id": bound}]


def test_the_window_lists_its_messages_in_id_order():
    assert [m["id"] for m in run(audit.MESSAGES_SQL, after=19, last=40)] == [20, 21, 30, 31, 40]


def test_the_context_holds_earlier_user_and_assistant_messages_of_the_window_conversations():
    assert [m["id"] for m in run(audit.CONTEXT_SQL, after=0, first=19, last=31)] == [10, 11]


def test_conversations_of_the_window_are_paginated_by_id():
    first = run(audit.CONVERSATIONS_SQL, after="0", first=19, last=40)

    assert [c["id"] for c in first] == [C1, C2, FORK]
    assert run(audit.CONVERSATIONS_SQL, after=C2, first=19, last=40)[0]["forked_from"] == C1
