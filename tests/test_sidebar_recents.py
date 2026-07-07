"""Tests for the out-of-band refresh of the sidebar recent-conversations block."""

from web.database import store


def headers(email="alice@example.com", **extra):
    return {"X-Forwarded-Email": email, **extra}


def test_recents_container_always_present_and_empty(client):
    html = client.get("/", headers=headers()).text

    assert 'id="sidebar-recents"' in html
    assert "sidebar-conversations is-empty" in html


def test_recents_marked_oob_on_htmx_request(client):
    html = client.get("/", headers=headers(**{"HX-Request": "true"})).text

    assert 'id="sidebar-recents"' in html
    assert 'hx-swap-oob="true"' in html


def test_recents_not_oob_on_full_page_load(client):
    html = client.get("/", headers=headers()).text

    assert 'hx-swap-oob="true"' not in html


def test_recents_lists_user_conversation_without_empty_modifier(client):
    conv = store.create_conversation(user_id="alice@example.com")
    store.update_conversation(conv.id, title="Ma conv récente")

    html = client.get("/", headers=headers()).text

    assert f"/explorations/{conv.id}" in html
    assert "is-empty" not in html
