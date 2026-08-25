from datetime import datetime, timezone

import pytest

from web.database import store
from web.db import get_db
from web.models import Dashboard

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]


def _h(email="alice@x"):
    return {"X-Forwarded-Email": email}


def _make_conversation(user_id="carol@x", title="Ma conversation"):
    conv = store.create_conversation(user_id=user_id)
    store.update_conversation(conv.id, title=title)
    return conv.id


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
    if item_type == "report":
        return str(_make_report())
    return _make_dashboard()


def test_home_shows_my_favorites_in_order(client):
    conv_id = _make_conversation()
    slug = _make_dashboard()
    store.add_favorite("alice@x", "app", slug)
    store.add_favorite("alice@x", "conversation", conv_id)

    html = client.get("/", headers=_h()).text

    assert "Favoris" in html
    assert html.index("Mon TDB") < html.index("Ma conversation")


def test_home_shows_a_favorite_report(client):
    report_id = _make_report()
    store.add_favorite("alice@x", "report", str(report_id))

    html = client.get("/", headers=_h()).text

    assert "Mon rapport" in html


def test_home_hides_favorites_of_other_users(client):
    conv_id = _make_conversation(user_id="bob@x")
    store.add_favorite("bob@x", "conversation", conv_id)

    html = client.get("/", headers=_h("alice@x")).text

    assert "Ma conversation" not in html


def test_home_shows_an_empty_state_when_i_have_no_favorite(client):
    html = client.get("/", headers=_h()).text

    assert "Aucun favori" in html


def test_home_skips_favorites_pointing_at_a_deleted_item(client):
    conv_id = _make_conversation()
    store.add_favorite("alice@x", "conversation", conv_id)
    store.delete_conversation(conv_id)

    response = client.get("/", headers=_h())

    assert response.status_code == 200
    assert "Ma conversation" not in response.text


def test_home_no_longer_shows_the_data_sources_block(client):
    html = client.get("/", headers=_h()).text

    assert "Sources de données" not in html


def test_home_shows_pinned_above_favorites(client):
    conv_id = _make_conversation()
    store.pin_conversation(conv_id, "Épinglé par un admin")
    store.add_favorite("alice@x", "conversation", conv_id)

    html = client.get("/", headers=_h()).text

    assert html.index("</i>Épinglés") < html.index("</i>Favoris")


def test_favorite_tiles_carry_the_full_title_for_hover(client):
    conv_id = _make_conversation()
    store.add_favorite("alice@x", "conversation", conv_id)

    html = client.get("/", headers=_h()).text

    assert 'title="Ma conversation"' in html


@pytest.mark.parametrize(
    "item_type,expected",
    [("conversation", "Ma conversation"), ("report", "Label admin"), ("app", "Label admin")],
)
def test_a_pin_label_wins_except_for_conversations(client, item_type, expected):
    item_id = _make_item(item_type)
    store.pin_item(item_type, item_id, "Label admin")

    html = client.get("/", headers=_h()).text

    assert expected in html


def test_a_pinned_conversation_without_title_falls_back_to_its_label(client):
    conv_id = _make_conversation(title=None)
    store.pin_item("conversation", conv_id, "Label admin")

    html = client.get("/", headers=_h()).text

    assert "Label admin" in html


def test_navigation_links_to_the_knowledge_pages(client):
    html = client.get("/", headers=_h()).text

    assert html.count('href="/connaissances"') == 2
    assert "Connaissances" in html


def test_the_knowledge_link_is_marked_active_on_the_knowledge_page(client):
    html = client.get("/connaissances", headers=_h()).text

    index = html.index('href="/connaissances"')
    assert 'aria-current="page"' in html[index : index + 200]


def _count_queries(fn):
    from sqlalchemy import event

    from web.db import get_engine

    engine = get_engine()
    count = 0

    def before(*args, **kwargs):
        nonlocal count
        count += 1

    event.listen(engine, "before_cursor_execute", before)
    try:
        fn()
    finally:
        event.remove(engine, "before_cursor_execute", before)
    return count


def test_the_home_page_query_count_does_not_grow_with_favorites(client):
    conv_id = _make_conversation()
    store.add_favorite("alice@x", "conversation", conv_id)
    one = _count_queries(lambda: client.get("/", headers=_h()))

    for _ in range(5):
        store.add_favorite("alice@x", "conversation", _make_conversation())
    six = _count_queries(lambda: client.get("/", headers=_h()))

    assert six == one
