"""Tests for the out-of-band refresh of the sidebar recent-conversations block."""

import pytest

from web.database import store


def headers(email="alice@example.com", **extra):
    return {"X-Forwarded-Email": email, **extra}


def test_recents_containers_always_present_and_empty(client):
    html = client.get("/", headers=headers()).text

    assert 'id="sidebar-recents"' in html
    assert 'id="mobile-recents"' in html
    assert "sidebar-conversations is-empty" in html


@pytest.mark.parametrize("extra, oob_expected", [({"HX-Request": "true"}, True), ({}, False)])
def test_recents_oob_marker_depends_on_htmx(client, extra, oob_expected):
    html = client.get("/", headers=headers(**extra)).text

    assert ('hx-swap-oob="true"' in html) is oob_expected
    assert ('id="mobile-recents" hx-swap-oob="true"' in html) is oob_expected


def test_recents_lists_user_conversation_without_empty_modifier(client):
    conv = store.create_conversation(user_id="alice@example.com")
    store.update_conversation(conv.id, title="Ma conv récente")

    html = client.get("/", headers=headers()).text

    assert f"/explorations/{conv.id}" in html
    assert 'class="sidebar-conversations is-empty"' not in html


def test_recents_populated_and_oob_on_htmx_request(client):
    conv = store.create_conversation(user_id="alice@example.com")
    store.update_conversation(conv.id, title="Ma conv récente")

    html = client.get("/", headers=headers(**{"HX-Request": "true"})).text

    assert 'hx-swap-oob="true"' in html
    assert f"/explorations/{conv.id}" in html
    assert 'class="sidebar-conversations is-empty"' not in html
