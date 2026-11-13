import json
from datetime import datetime, timezone

import pytest

from web.config import ADMIN_USERS
from web.database import store
from web.db import get_db
from web.models import Dashboard, DashboardPublication

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

ADMIN = ADMIN_USERS[0]


def _headers(email=ADMIN):
    return {"X-Forwarded-Email": email}


def _make_dashboard(slug, conv_id=None, *, has_api_access=False):
    now = datetime.now(timezone.utc)
    with get_db() as session:
        session.add(
            Dashboard(
                slug=slug,
                title=slug,
                description="d",
                website="emplois",
                category="c",
                first_author_email="alice@x",
                is_archived=False,
                has_api_access=has_api_access,
                has_cron=False,
                has_persistence=False,
                created_in_conversation_id=conv_id,
                created_at=now,
                updated_at=now,
            )
        )


def _publish(slug, environment="production", publication_id="convd1"):
    with get_db() as session:
        session.add(
            DashboardPublication(
                dashboard_slug=slug,
                publication_id=publication_id,
                environment=environment,
                published_by="alice@x",
                published_at=datetime.now(timezone.utc),
                snapshot_has_cron=False,
            )
        )


def _tool_wrote(conv_id, file_path):
    store.add_message(conv_id, "tool_use", json.dumps({"tool": "Edit", "input": {"file_path": file_path}}))


def test_dod_10_conversation_signale_un_tableau_publie_modifie_depuis(client, mocker):
    mocker.patch("web.publications.snapshot_drifted", return_value=True)
    conv = store.create_conversation(user_id=ADMIN)
    _make_dashboard("conv-drift", conv.id)
    _publish("conv-drift")

    r = client.get(f"/api/conversations/{conv.id}/dashboards", headers=_headers())

    assert r.status_code == 200
    drifted = r.json()["drifted"]
    assert [d["slug"] for d in drifted] == ["conv-drift"]
    assert drifted[0]["title"] == "conv-drift"


def test_un_tableau_cree_ailleurs_mais_modifie_ici_est_signale(client, mocker):
    mocker.patch("web.publications.snapshot_drifted", return_value=True)
    conv = store.create_conversation(user_id=ADMIN)
    _make_dashboard("ext-tdb", conv_id="une-autre-conversation")
    _publish("ext-tdb")
    _tool_wrote(conv.id, "/app/data/interactive/ext-tdb/app.js")

    r = client.get(f"/api/conversations/{conv.id}/dashboards", headers=_headers())

    assert [d["slug"] for d in r.json()["drifted"]] == ["ext-tdb"]


def test_un_tableau_publie_non_touche_ici_n_est_pas_signale(client, mocker):
    mocker.patch("web.publications.snapshot_drifted", return_value=True)
    conv = store.create_conversation(user_id=ADMIN)
    _make_dashboard("ailleurs-tdb", conv_id="une-autre-conversation")
    _publish("ailleurs-tdb")

    r = client.get(f"/api/conversations/{conv.id}/dashboards", headers=_headers())

    assert r.json()["drifted"] == []


def test_conversation_dashboards_denied_to_non_owner(client):
    conv = store.create_conversation(user_id="owner@x")
    r = client.get(f"/api/conversations/{conv.id}/dashboards", headers=_headers("intruder@x"))
    assert r.status_code == 403


def test_conversation_dashboards_unknown_conversation_is_404(client):
    r = client.get("/api/conversations/does-not-exist/dashboards", headers=_headers())
    assert r.status_code == 404


@pytest.mark.parametrize("setup", ["no_publication", "up_to_date"])
def test_dod_11_conversation_sans_tableau_publie_ou_a_jour_ne_signale_rien(client, mocker, setup):
    mocker.patch("web.publications.snapshot_drifted", return_value=False)
    conv = store.create_conversation(user_id=ADMIN)
    _make_dashboard(f"conv-{setup}", conv.id)
    if setup == "up_to_date":
        _publish(f"conv-{setup}")

    r = client.get(f"/api/conversations/{conv.id}/dashboards", headers=_headers())

    assert r.status_code == 200
    assert r.json()["drifted"] == []
