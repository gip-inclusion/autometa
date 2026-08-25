from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

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
