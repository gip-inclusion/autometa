from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from web.database import store
from web.db import get_db
from web.models import UserFavorite

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]


@pytest.fixture(autouse=True)
def _clean_favorites():
    with get_db() as session:
        session.execute(text("TRUNCATE TABLE user_favorites"))
    yield


def add(user_id, item_type, item_id, position=0):
    with get_db() as session:
        session.add(
            UserFavorite(
                user_id=user_id,
                item_type=item_type,
                item_id=item_id,
                position=position,
                created_at=datetime.now(timezone.utc),
            )
        )


def test_the_same_item_cannot_be_favorited_twice_by_the_same_user():
    add("a@x", "conversation", "c1")

    with pytest.raises(IntegrityError):
        add("a@x", "conversation", "c1", position=1)


def test_two_users_can_favorite_the_same_item():
    add("a@x", "conversation", "c1")
    add("b@x", "conversation", "c1")

    with get_db() as session:
        rows = session.scalars(select(UserFavorite).where(UserFavorite.item_id == "c1")).all()
        assert sorted(r.user_id for r in rows) == ["a@x", "b@x"]


def test_add_favorite_is_idempotent_and_appends_at_the_end():
    store.add_favorite("a@x", "conversation", "c1")
    store.add_favorite("a@x", "app", "tdb-1")
    store.add_favorite("a@x", "conversation", "c1")

    favorites = store.list_favorites("a@x")
    assert [(f.item_type, f.item_id, f.position) for f in favorites] == [
        ("conversation", "c1", 0),
        ("app", "tdb-1", 1),
    ]


def test_favorites_are_scoped_to_their_user():
    store.add_favorite("a@x", "conversation", "c1")
    store.add_favorite("b@x", "report", "7")

    assert [f.item_id for f in store.list_favorites("a@x")] == ["c1"]
    assert store.get_favorite_ids("a@x") == {("conversation", "c1")}
    assert store.get_favorite_ids("b@x") == {("report", "7")}


@pytest.mark.parametrize("item_type,item_id", [("conversation", "c1"), ("report", "7"), ("app", "tdb-1")])
def test_remove_favorite_is_idempotent(item_type, item_id):
    store.add_favorite("a@x", item_type, item_id)
    assert store.remove_favorite("a@x", item_type, item_id) is True
    assert store.remove_favorite("a@x", item_type, item_id) is False
    assert store.list_favorites("a@x") == []


def test_reorder_favorites_renumbers_from_zero():
    for item_id in ("c1", "c2", "c3"):
        store.add_favorite("a@x", "conversation", item_id)

    store.reorder_favorites("a@x", [("conversation", "c3"), ("conversation", "c1")])

    assert [(f.item_id, f.position) for f in store.list_favorites("a@x")] == [
        ("c3", 0),
        ("c1", 1),
        ("c2", 2),
    ]


def test_reorder_favorites_ignores_items_that_are_not_mine():
    store.add_favorite("a@x", "conversation", "c1")
    store.add_favorite("b@x", "conversation", "c2")

    store.reorder_favorites("a@x", [("conversation", "c2"), ("conversation", "c1")])

    assert [f.item_id for f in store.list_favorites("a@x")] == ["c1"]
    assert [f.item_id for f in store.list_favorites("b@x")] == ["c2"]


def test_reorder_favorites_matches_integer_item_ids():
    store.add_favorite("a@x", "conversation", "c1")
    store.add_favorite("a@x", "report", 7)

    store.reorder_favorites("a@x", [("report", 7), ("conversation", "c1")])

    assert [(f.item_type, f.item_id) for f in store.list_favorites("a@x")] == [
        ("report", "7"),
        ("conversation", "c1"),
    ]


def test_deleting_a_conversation_removes_it_from_everyones_favorites():
    conv = store.create_conversation(user_id="carol@x")
    store.add_favorite("a@x", "conversation", conv.id)
    store.add_favorite("b@x", "conversation", conv.id)

    store.delete_conversation(conv.id)

    assert store.list_favorites("a@x") == []
    assert store.list_favorites("b@x") == []


def test_deleting_a_report_removes_it_from_everyones_favorites():
    report_id = store.create_report(title="Mon rapport", content="contenu", user_id="carol@x").id
    store.add_favorite("a@x", "report", str(report_id))
    store.add_favorite("b@x", "report", str(report_id))

    store.delete_report(report_id)

    assert store.list_favorites("a@x") == []
    assert store.list_favorites("b@x") == []


def test_deleting_a_conversation_also_removes_favorites_of_its_reports():
    conv = store.create_conversation(user_id="carol@x")
    report = store.create_report(
        title="Rapport de conversation", content="contenu", source_conversation_id=conv.id, user_id="carol@x"
    )
    with get_db() as session:
        session.execute(
            text("UPDATE reports SET conversation_id = :conv_id WHERE id = :report_id"),
            {"conv_id": conv.id, "report_id": report.id},
        )
    store.add_favorite("a@x", "report", str(report.id))

    store.delete_conversation(conv.id)

    assert store.list_favorites("a@x") == []


def test_archiving_a_report_keeps_it_in_favorites():
    report_id = store.create_report(title="Mon rapport", content="contenu", user_id="carol@x").id
    store.add_favorite("a@x", "report", str(report_id))

    store.archive_report(report_id)

    assert [f.item_id for f in store.list_favorites("a@x")] == [str(report_id)]
