from datetime import datetime, timezone

import pytest

from web.config import ADMIN_USERS
from web.database import store
from web.db import get_db
from web.models import Dashboard

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

ADMIN = ADMIN_USERS[0]


def _h(email="alice@x"):
    return {"X-Forwarded-Email": email}


def _make_conversation(user_id="alice@x"):
    return store.create_conversation(user_id=user_id).id


def _make_dashboard(slug="tdb-1", *, archived=False):
    now = datetime.now(timezone.utc)
    with get_db() as session:
        session.add(
            Dashboard(
                slug=slug,
                title="Mon TDB",
                description="desc",
                website="emplois",
                category="c",
                first_author_email="alice@x",
                is_archived=archived,
                has_api_access=False,
                has_cron=False,
                has_persistence=False,
                created_at=now,
                updated_at=now,
            )
        )
    return slug


def test_add_and_remove_a_favorite_conversation(client):
    conv_id = _make_conversation()

    assert client.post(f"/api/favorites/conversation/{conv_id}", headers=_h()).status_code == 200
    assert store.get_favorite_ids("alice@x") == {("conversation", conv_id)}

    assert client.delete(f"/api/favorites/conversation/{conv_id}", headers=_h()).status_code == 200
    assert store.get_favorite_ids("alice@x") == set()


@pytest.mark.parametrize("item_type,item_id", [("conversation", "nope"), ("report", "999"), ("app", "nope")])
def test_favoriting_a_missing_item_is_a_404(client, item_type, item_id):
    assert client.post(f"/api/favorites/{item_type}/{item_id}", headers=_h()).status_code == 404


def test_unknown_item_type_is_rejected(client):
    assert client.post("/api/favorites/banana/x", headers=_h()).status_code == 422


def test_a_user_cannot_see_or_touch_another_users_favorites(client):
    conv_id = _make_conversation()
    client.post(f"/api/favorites/conversation/{conv_id}", headers=_h("alice@x"))

    client.delete(f"/api/favorites/conversation/{conv_id}", headers=_h("bob@x"))

    assert store.get_favorite_ids("alice@x") == {("conversation", conv_id)}
    assert store.get_favorite_ids("bob@x") == set()


def test_pinning_does_not_create_a_favorite_and_the_reverse(client):
    conv_id = _make_conversation()

    client.post(f"/api/conversations/{conv_id}/pin", headers=_h(ADMIN), json={})
    assert store.get_favorite_ids(ADMIN) == set()

    client.post(f"/api/favorites/conversation/{conv_id}", headers=_h(ADMIN))
    assert store.get_pinned_ids() == {("conversation", conv_id)}


def test_favoriting_the_same_item_twice_stays_ok(client):
    conv_id = _make_conversation()

    assert client.post(f"/api/favorites/conversation/{conv_id}", headers=_h()).status_code == 200
    assert client.post(f"/api/favorites/conversation/{conv_id}", headers=_h()).status_code == 200
    assert store.get_favorite_ids("alice@x") == {("conversation", conv_id)}


def test_an_archived_dashboard_cannot_be_favorited(client):
    slug = _make_dashboard(archived=True)

    assert client.post(f"/api/favorites/app/{slug}", headers=_h()).status_code == 404


@pytest.mark.parametrize(
    "body",
    [{"items": "x"}, {"items": [{"item_type": "app"}]}, {}],
)
def test_a_malformed_reorder_body_is_a_400(client, body):
    response = client.patch("/api/favorites/order", headers=_h(), json=body)

    assert response.status_code == 400


def test_an_empty_reorder_body_is_a_400(client):
    response = client.patch("/api/favorites/order", headers=_h(), content=b"")

    assert response.status_code == 400


def test_reordering_persists_the_new_order(client):
    conv_id = _make_conversation()
    slug = _make_dashboard()
    client.post(f"/api/favorites/conversation/{conv_id}", headers=_h())
    client.post(f"/api/favorites/app/{slug}", headers=_h())

    response = client.patch(
        "/api/favorites/order",
        headers=_h(),
        json={"items": [{"item_type": "app", "item_id": slug}, {"item_type": "conversation", "item_id": conv_id}]},
    )

    assert response.status_code == 200
    assert [f.item_id for f in store.list_favorites("alice@x")] == [slug, conv_id]
