"""Tests for conversation flag feature (user toggle + admin dashboard endpoints)."""

import pytest

from web.database import store
from web.deps import templates


@pytest.fixture
def conv(app):
    c = store.create_conversation(user_id="owner@example.com")
    store.update_conversation(c.id, title="Sample conversation")
    return c


@pytest.fixture
def admin_headers():
    return {"X-Forwarded-Email": "admin@localhost"}


@pytest.fixture
def alice_headers():
    return {"X-Forwarded-Email": "alice@example.com"}


@pytest.fixture
def bob_headers():
    return {"X-Forwarded-Email": "bob@example.com"}


def _post_flag(client, conv_id, headers, reason="x"):
    return client.post(f"/api/conversations/{conv_id}/flag", data={"reason": reason}, headers=headers)


class TestPostFlag:
    def test_flag_unflagged_conversation(self, app, client, conv, alice_headers):
        resp = _post_flag(client, conv.id, alice_headers, reason="la réponse est hors sujet")
        assert resp.status_code == 200
        assert 'id="chatFlagBtn"' in resp.text
        assert "flagged" in resp.text
        assert 'data-can-remove="1"' in resp.text
        assert 'data-current-reason="la réponse est hors sujet"' in resp.text

    def test_flag_overwrites_reason_for_same_user(self, app, client, conv, alice_headers):
        _post_flag(client, conv.id, alice_headers, reason="first")
        resp = _post_flag(client, conv.id, alice_headers, reason="second")
        assert resp.status_code == 200
        assert 'data-current-reason="second"' in resp.text

    def test_overwrite_by_different_user(self, app, client, conv, admin_headers, alice_headers, bob_headers):
        _post_flag(client, conv.id, alice_headers, reason="alice")
        _post_flag(client, conv.id, bob_headers, reason="bob")
        flagged = client.get("/api/conversations/flagged", headers=admin_headers).json()["conversations"]
        assert flagged[0]["user_id"] == "bob@example.com"
        assert flagged[0]["flag_reason"] == "bob"

    def test_empty_reason_allowed(self, app, client, conv, alice_headers):
        resp = _post_flag(client, conv.id, alice_headers, reason="")
        assert resp.status_code == 200
        assert 'data-current-reason=""' in resp.text

    def test_reason_too_long_rejected(self, app, client, conv, alice_headers):
        resp = _post_flag(client, conv.id, alice_headers, reason="a" * 501)
        assert resp.status_code == 422

    def test_flag_nonexistent_conversation(self, app, client, alice_headers):
        resp = _post_flag(client, "does-not-exist", alice_headers)
        assert resp.status_code == 404


class TestGetFlagged:
    def test_admin_sees_flagged_sorted_desc(self, app, client, admin_headers, alice_headers):
        c1 = store.create_conversation(user_id="owner@example.com")
        c2 = store.create_conversation(user_id="owner@example.com")
        store.update_conversation(c1.id, title="First")
        store.update_conversation(c2.id, title="Second")

        _post_flag(client, c1.id, alice_headers, reason="R1")
        _post_flag(client, c2.id, alice_headers, reason="R2")

        resp = client.get("/api/conversations/flagged", headers=admin_headers)
        assert resp.status_code == 200
        convs = resp.json()["conversations"]
        assert len(convs) == 2
        assert convs[0]["id"] == c2.id
        assert convs[0]["title"] == "Second"
        assert convs[0]["user_id"] == "alice@example.com"
        assert convs[0]["flag_reason"] == "R2"
        assert convs[0]["flagged_at"] is not None
        assert convs[1]["id"] == c1.id

    def test_admin_sees_empty_list(self, app, client, admin_headers):
        resp = client.get("/api/conversations/flagged", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == {"conversations": []}

    def test_non_admin_forbidden(self, app, client, alice_headers):
        resp = client.get("/api/conversations/flagged", headers=alice_headers)
        assert resp.status_code == 403

    def test_user_id_is_flagger_not_owner(self, app, client, conv, admin_headers, alice_headers):
        _post_flag(client, conv.id, alice_headers, reason="R")
        resp = client.get("/api/conversations/flagged", headers=admin_headers)
        convs = resp.json()["conversations"]
        assert convs[0]["user_id"] == "alice@example.com"
        assert convs[0]["user_id"] != "owner@example.com"


class TestDeleteFlag:
    def test_admin_removes_flag(self, app, client, conv, admin_headers, alice_headers):
        _post_flag(client, conv.id, alice_headers, reason="R")
        resp = client.delete(f"/api/conversations/{conv.id}/flag", headers=admin_headers)
        assert resp.status_code == 200
        assert 'id="chatFlagBtn"' in resp.text
        assert "flagged" not in resp.text

        flagged = client.get("/api/conversations/flagged", headers=admin_headers).json()["conversations"]
        assert flagged == []

    def test_flagger_can_remove_own_flag(self, app, client, conv, alice_headers):
        _post_flag(client, conv.id, alice_headers, reason="R")
        resp = client.delete(f"/api/conversations/{conv.id}/flag", headers=alice_headers)
        assert resp.status_code == 200
        assert "flagged" not in resp.text

    def test_other_user_cannot_remove_flag(self, app, client, conv, alice_headers, bob_headers):
        _post_flag(client, conv.id, alice_headers, reason="R")
        resp = client.delete(f"/api/conversations/{conv.id}/flag", headers=bob_headers)
        assert resp.status_code == 403

    def test_delete_is_idempotent_for_flagger(self, app, client, conv, alice_headers):
        _post_flag(client, conv.id, alice_headers, reason="R")
        first = client.delete(f"/api/conversations/{conv.id}/flag", headers=alice_headers)
        assert first.status_code == 200
        second = client.delete(f"/api/conversations/{conv.id}/flag", headers=alice_headers)
        assert second.status_code == 200

    def test_delete_nonexistent_conversation(self, app, client, admin_headers):
        resp = client.delete("/api/conversations/does-not-exist/flag", headers=admin_headers)
        assert resp.status_code == 404


class TestCascadeOnConversationDelete:
    def test_deleting_flagged_conversation_removes_it_from_dashboard(
        self, app, client, conv, admin_headers, alice_headers
    ):
        _post_flag(client, conv.id, alice_headers, reason="R")
        resp = client.delete(f"/api/conversations/{conv.id}", headers=admin_headers)
        assert resp.status_code == 200

        resp = client.get("/api/conversations/flagged", headers=admin_headers)
        assert resp.json()["conversations"] == []


class TestRenderFlagButton:
    @pytest.mark.parametrize(
        "flagged_by,expected_flagged_class,expected_can_remove",
        [
            (None, False, False),
            ("alice@example.com", True, True),
            ("bob@example.com", True, False),
        ],
    )
    def test_flag_button_state(
        self,
        app,
        client,
        conv,
        alice_headers,
        flagged_by,
        expected_flagged_class,
        expected_can_remove,
    ):
        if flagged_by:
            _post_flag(client, conv.id, {"X-Forwarded-Email": flagged_by}, reason="test reason")

        resp = client.get(f"/explorations/{conv.id}", headers=alice_headers)
        assert resp.status_code == 200
        html = resp.text

        assert 'id="chatFlagBtn"' in html
        assert 'id="flagDialog"' in html
        assert 'maxlength="500"' in html
        assert 'id="flagRemove"' in html

        button_tag = next(chunk for chunk in html.split("<button") if 'id="chatFlagBtn"' in chunk).split(">", 1)[0]
        assert ("chat-flag-btn flagged" in button_tag) is expected_flagged_class
        assert ('data-can-remove="1"' in button_tag) is expected_can_remove

    def test_admin_sees_can_remove_on_other_user_flag(self, app, client, conv, admin_headers, alice_headers):
        _post_flag(client, conv.id, alice_headers, reason="R")
        resp = client.get(f"/explorations/{conv.id}", headers=admin_headers)
        assert resp.status_code == 200
        button_tag = next(chunk for chunk in resp.text.split("<button") if 'id="chatFlagBtn"' in chunk).split(">", 1)[0]
        assert 'data-can-remove="1"' in button_tag


class TestTemplateGlobalsSanity:
    def test_templates_env_is_importable(self):
        assert templates is not None
        assert "static_url" in templates.env.globals
