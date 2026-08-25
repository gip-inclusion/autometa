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


def _make_conversation():
    return store.create_conversation(user_id="alice@x").id


def _make_dashboard():
    slug = "tdb-1"
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
                is_archived=False,
                has_api_access=False,
                has_cron=False,
                has_persistence=False,
                created_at=now,
                updated_at=now,
            )
        )
    return slug


def _make_report():
    return store.create_report(title="Mon rapport", content="contenu", user_id="alice@x").id


def _make_item(item_type):
    if item_type == "conversation":
        return _make_conversation()
    return str(_make_report())


def _window_around(html, needle):
    index = html.index(needle)
    return html[index - 300 : index + 300]


@pytest.mark.parametrize(
    "path",
    ["/conversations?show=convos", "/conversations?show=reports", "/dashboards"],
)
def test_lists_offer_a_favorite_star(client, path):
    _make_conversation()
    _make_dashboard()
    _make_report()

    html = client.get(path, headers=_h()).text

    assert "toggleFavorite(this)" in html


def test_dashboard_page_offers_a_favorite_star(client):
    slug = _make_dashboard()

    html = client.get(f"/dashboards/{slug}/edit", headers=_h()).text

    assert "toggleFavorite(this)" in html


def test_conversation_page_offers_a_favorite_star(client):
    conv_id = _make_conversation()

    html = client.get(f"/explorations/{conv_id}", headers=_h()).text

    assert "toggleFavorite(this)" in html


@pytest.mark.parametrize(
    "item_type,path",
    [("conversation", "/conversations?show=convos"), ("report", "/conversations?show=reports")],
)
def test_the_star_is_filled_for_an_item_i_already_favorited(client, item_type, path):
    item_id = _make_item(item_type)
    store.add_favorite("alice@x", item_type, item_id)

    html = client.get(path, headers=_h()).text

    assert "ri-star-fill" in _window_around(html, f'data-item-id="{item_id}"')


def test_the_star_is_empty_for_an_item_i_have_not_favorited(client):
    conv_id = _make_conversation()

    html = client.get("/conversations?show=convos", headers=_h()).text

    assert "ri-star-line" in _window_around(html, f'data-item-id="{conv_id}"')


def test_the_star_announces_its_state_to_assistive_tech(client):
    conv_id = _make_conversation()
    store.add_favorite("alice@x", "conversation", conv_id)

    html = client.get("/conversations?show=convos", headers=_h()).text

    assert 'aria-pressed="true"' in _window_around(html, f'data-item-id="{conv_id}"')


@pytest.mark.parametrize("email,pin_expected", [("alice@x", False), (ADMIN, True)])
def test_the_star_is_offered_to_everyone_but_the_pin_is_admin_only(client, email, pin_expected):
    _make_conversation()

    html = client.get("/conversations?show=convos", headers=_h(email)).text

    assert "toggleFavorite(this)" in html
    assert ("togglePin('/api/conversations/" in html) == pin_expected


def test_the_star_in_a_conversation_header_uses_the_header_button_style(client):
    conv_id = _make_conversation()

    window = _window_around(client.get(f"/explorations/{conv_id}", headers=_h()).text, f'data-item-id="{conv_id}"')

    assert "conv-action-btn" in window
    assert "conv-item-action-btn" not in window


def test_the_star_on_a_dashboard_page_uses_the_page_button_style(client):
    slug = _make_dashboard()

    window = _window_around(client.get(f"/dashboards/{slug}/edit", headers=_h()).text, f'data-item-id="{slug}"')

    assert "btn-outline-secondary" in window
    assert "conv-item-action-btn" not in window


def test_the_star_in_a_list_keeps_the_hover_revealed_style(client):
    conv_id = _make_conversation()

    window = _window_around(client.get("/conversations?show=convos", headers=_h()).text, f'data-item-id="{conv_id}"')

    assert "conv-item-action-btn" in window
