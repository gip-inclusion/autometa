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


class TestPostFlag:
    def test_flag_unflagged_conversation(self, app, client, conv, alice_headers):
        resp = client.post(
            f"/api/conversations/{conv.id}/flag",
            json={"reason": "la réponse est hors sujet"},
            headers=alice_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["flagged"] is True
        assert data["flag_reason"] == "la réponse est hors sujet"
        assert data["flag_user_id"] == "alice@example.com"
        assert data["flagged_at"] is not None

    def test_toggle_off_by_same_user(self, app, client, conv, alice_headers):
        client.post(f"/api/conversations/{conv.id}/flag", json={"reason": "x"}, headers=alice_headers)
        resp = client.post(f"/api/conversations/{conv.id}/flag", json={"reason": "x"}, headers=alice_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["flagged"] is False
        assert data["flag_reason"] is None
        assert data["flag_user_id"] is None
        assert data["flagged_at"] is None

    def test_overwrite_by_different_user(self, app, client, conv, alice_headers, bob_headers):
        client.post(f"/api/conversations/{conv.id}/flag", json={"reason": "alice"}, headers=alice_headers)
        resp = client.post(f"/api/conversations/{conv.id}/flag", json={"reason": "bob"}, headers=bob_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["flagged"] is True
        assert data["flag_user_id"] == "bob@example.com"
        assert data["flag_reason"] == "bob"

    def test_empty_reason_allowed(self, app, client, conv, alice_headers):
        resp = client.post(f"/api/conversations/{conv.id}/flag", json={}, headers=alice_headers)
        assert resp.status_code == 200
        assert resp.json()["flag_reason"] == ""

    def test_reason_too_long_rejected(self, app, client, conv, alice_headers):
        resp = client.post(
            f"/api/conversations/{conv.id}/flag",
            json={"reason": "a" * 501},
            headers=alice_headers,
        )
        assert resp.status_code == 422

    def test_flag_nonexistent_conversation(self, app, client, alice_headers):
        resp = client.post("/api/conversations/does-not-exist/flag", json={}, headers=alice_headers)
        assert resp.status_code == 404


class TestGetFlagged:
    def test_admin_sees_flagged_sorted_desc(self, app, client, admin_headers, alice_headers):
        c1 = store.create_conversation(user_id="owner@example.com")
        c2 = store.create_conversation(user_id="owner@example.com")
        store.update_conversation(c1.id, title="First")
        store.update_conversation(c2.id, title="Second")

        client.post(f"/api/conversations/{c1.id}/flag", json={"reason": "R1"}, headers=alice_headers)
        client.post(f"/api/conversations/{c2.id}/flag", json={"reason": "R2"}, headers=alice_headers)

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
        client.post(f"/api/conversations/{conv.id}/flag", json={"reason": "R"}, headers=alice_headers)
        resp = client.get("/api/conversations/flagged", headers=admin_headers)
        convs = resp.json()["conversations"]
        assert convs[0]["user_id"] == "alice@example.com"
        assert convs[0]["user_id"] != "owner@example.com"


class TestDeleteFlag:
    def test_admin_removes_flag(self, app, client, conv, admin_headers, alice_headers):
        client.post(f"/api/conversations/{conv.id}/flag", json={"reason": "R"}, headers=alice_headers)
        resp = client.delete(f"/api/conversations/{conv.id}/flag", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == {"flagged": False}

        resp = client.get("/api/conversations/flagged", headers=admin_headers)
        assert resp.json()["conversations"] == []

    def test_admin_delete_is_idempotent(self, app, client, conv, admin_headers):
        resp1 = client.delete(f"/api/conversations/{conv.id}/flag", headers=admin_headers)
        resp2 = client.delete(f"/api/conversations/{conv.id}/flag", headers=admin_headers)
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp2.json() == {"flagged": False}

    def test_non_admin_forbidden(self, app, client, conv, alice_headers):
        resp = client.delete(f"/api/conversations/{conv.id}/flag", headers=alice_headers)
        assert resp.status_code == 403

    def test_delete_nonexistent_conversation(self, app, client, admin_headers):
        resp = client.delete("/api/conversations/does-not-exist/flag", headers=admin_headers)
        assert resp.status_code == 404


class TestCascadeOnConversationDelete:
    def test_deleting_flagged_conversation_removes_it_from_dashboard(
        self, app, client, conv, admin_headers, alice_headers
    ):
        client.post(f"/api/conversations/{conv.id}/flag", json={"reason": "R"}, headers=alice_headers)
        resp = client.delete(f"/api/conversations/{conv.id}", headers=admin_headers)
        assert resp.status_code == 200

        resp = client.get("/api/conversations/flagged", headers=admin_headers)
        assert resp.json()["conversations"] == []


class TestRenderFlagButton:
    @pytest.mark.parametrize(
        "flagged_by_current_user,expected_classes,expected_remove_button_visible",
        [
            (None, [], False),
            ("alice@example.com", ["flagged"], True),
            ("bob@example.com", ["flagged"], False),
        ],
    )
    def test_flag_button_state(
        self,
        app,
        client,
        conv,
        alice_headers,
        flagged_by_current_user,
        expected_classes,
        expected_remove_button_visible,
    ):
        if flagged_by_current_user:
            client.post(
                f"/api/conversations/{conv.id}/flag",
                json={"reason": "test reason"},
                headers={"X-Forwarded-Email": flagged_by_current_user},
            )

        resp = client.get(f"/explorations/{conv.id}", headers=alice_headers)
        assert resp.status_code == 200
        html = resp.text

        assert 'id="chatFlagBtn"' in html
        assert 'id="flagDialog"' in html
        assert 'maxlength="500"' in html

        for cls in expected_classes:
            assert cls in html

        if flagged_by_current_user == "alice@example.com":
            assert 'data-current-reason="test reason"' in html

        if expected_remove_button_visible:
            assert 'id="flagRemove"' in html and "hidden" not in html.split('id="flagRemove"')[1].split(">")[0]
        else:
            assert 'id="flagRemove"' in html and "hidden" in html.split('id="flagRemove"')[1].split(">")[0]


class TestTemplateGlobalsSanity:
    def test_templates_env_is_importable(self):
        assert templates is not None
        assert "static_url" in templates.env.globals
