from datetime import datetime, timedelta, timezone

import pytest

from web.config import ADMIN_USERS
from web.database import store
from web.db import get_db
from web.models import Dashboard, DashboardPublication

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

ADMIN = ADMIN_USERS[0]


def _headers(email=ADMIN):
    return {"X-Forwarded-Email": email}


def _make_dashboard(slug, conv_id, *, updated_at, has_api_access=False):
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
                created_at=updated_at,
                updated_at=updated_at,
            )
        )


def _publish(slug, environment, published_at, publication_id):
    with get_db() as session:
        session.add(
            DashboardPublication(
                dashboard_slug=slug,
                publication_id=publication_id,
                environment=environment,
                published_by="alice@x",
                published_at=published_at,
                snapshot_has_cron=False,
            )
        )


def test_dod_10_conversation_signale_un_tableau_publie_modifie_depuis(client):
    conv = store.create_conversation(user_id=ADMIN)
    now = datetime.now(timezone.utc)
    _make_dashboard("conv-drift", conv.id, updated_at=now)
    _publish("conv-drift", "production", now - timedelta(days=1), "convd1")

    r = client.get(f"/api/conversations/{conv.id}/dashboards", headers=_headers())

    assert r.status_code == 200
    drifted = r.json()["drifted"]
    assert [d["slug"] for d in drifted] == ["conv-drift"]
    assert drifted[0]["title"] == "conv-drift"


def test_conversation_dashboards_denied_to_non_owner(client):
    conv = store.create_conversation(user_id="owner@x")
    r = client.get(f"/api/conversations/{conv.id}/dashboards", headers=_headers("intruder@x"))
    assert r.status_code == 403


def test_conversation_dashboards_unknown_conversation_is_404(client):
    r = client.get("/api/conversations/does-not-exist/dashboards", headers=_headers())
    assert r.status_code == 404


@pytest.mark.parametrize("setup", ["no_publication", "up_to_date"])
def test_dod_11_conversation_sans_tableau_publie_ou_a_jour_ne_signale_rien(client, setup):
    conv = store.create_conversation(user_id=ADMIN)
    now = datetime.now(timezone.utc)
    _make_dashboard(f"conv-{setup}", conv.id, updated_at=now)
    if setup == "up_to_date":
        _publish(f"conv-{setup}", "production", now + timedelta(days=1), "convu1")

    r = client.get(f"/api/conversations/{conv.id}/dashboards", headers=_headers())

    assert r.status_code == 200
    assert r.json()["drifted"] == []
