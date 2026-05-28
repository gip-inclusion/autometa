from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from web.database import store
from web.db import get_db
from web.models import CronRun, Dashboard

ADMIN = "louisjean.teitelbaum@inclusion.gouv.fr"


def _make_dashboard(slug, *, archived=False, author="alice@x", title=None):
    now = datetime.now(timezone.utc)
    with get_db() as session:
        session.add(
            Dashboard(
                slug=slug,
                title=title or slug,
                description="desc",
                website="emplois",
                category="c",
                first_author_email=author,
                is_archived=archived,
                has_api_access=False,
                has_cron=False,
                has_persistence=False,
                created_at=now,
                updated_at=now,
            )
        )


def _h(email=ADMIN):
    return {"X-Forwarded-Email": email}


def test_latest_view_lists_active(client):
    _make_dashboard("latest-a")
    _make_dashboard("latest-archived", archived=True)
    r = client.get("/dashboards?view=latest", headers=_h())
    assert r.status_code == 200
    assert "latest-a" in r.text
    assert "latest-archived" not in r.text


def test_mine_view_filters_by_author(client):
    _make_dashboard("mine-yes", author="me@x")
    _make_dashboard("mine-no", author="other@x")
    r = client.get("/dashboards?view=mine", headers=_h("me@x"))
    assert r.status_code == 200
    assert "mine-yes" in r.text
    assert "mine-no" not in r.text


def test_archived_view_lists_archived_only(client):
    _make_dashboard("arch-active")
    _make_dashboard("arch-gone", archived=True)
    r = client.get("/dashboards?view=archived", headers=_h())
    assert r.status_code == 200
    assert "arch-gone" in r.text
    assert "arch-active" not in r.text


def test_featured_row_shows_pinned(client):
    _make_dashboard("feat-pinned")
    store.pin_item("app", "feat-pinned", "Feat Pinned")
    r = client.get("/dashboards", headers=_h())
    assert r.status_code == 200
    assert "À la une" in r.text
    assert "feat-pinned" in r.text


def test_featured_row_absent_without_pins(client):
    _make_dashboard("not-pinned")
    r = client.get("/dashboards", headers=_h())
    assert r.status_code == 200
    assert "À la une" not in r.text


def test_featured_skips_archived_pins(client):
    _make_dashboard("feat-archived", archived=True)
    store.pin_item("app", "feat-archived", "Archived")
    r = client.get("/dashboards", headers=_h())
    assert r.status_code == 200
    assert "À la une" not in r.text


def test_featured_preserves_pin_order(client):
    _make_dashboard("feat-second")
    _make_dashboard("feat-first")
    store.pin_item("app", "feat-first", "First")
    store.pin_item("app", "feat-second", "Second")
    r = client.get("/dashboards", headers=_h())
    assert r.status_code == 200
    assert r.text.index("feat-first") < r.text.index("feat-second")


def test_unknown_view_falls_back_to_latest(client):
    _make_dashboard("fallback-one")
    r = client.get("/dashboards?view=bogus", headers=_h())
    assert r.status_code == 200
    assert "fallback-one" in r.text


def test_detail_page_renders(client):
    _make_dashboard("detail-render", title="Mon TDB")
    r = client.get("/dashboards/detail-render/edit", headers=_h())
    assert r.status_code == 200
    assert "Mon TDB" in r.text


def test_bare_slug_redirects_to_edit(client):
    _make_dashboard("redir-me")
    r = client.get("/dashboards/redir-me", headers=_h(), follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/dashboards/redir-me/edit"


def test_detail_unknown_slug_redirects_to_list(client):
    r = client.get("/dashboards/nope/edit", headers=_h(), follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/dashboards"


def test_detail_bad_slug_rejected(client):
    r = client.get("/dashboards/Bad.Slug/edit", headers=_h())
    assert r.status_code == 422


@pytest.mark.parametrize("archived", [True, False])
def test_archive_toggle(client, archived):
    _make_dashboard("toggle-arch", archived=not archived)
    r = client.post("/api/dashboards/toggle-arch/archive", json={"archived": archived}, headers=_h())
    assert r.status_code == 200
    assert r.json() == {"slug": "toggle-arch", "is_archived": archived}
    with get_db() as session:
        d = session.scalar(select(Dashboard).where(Dashboard.slug == "toggle-arch"))
        assert d.is_archived is archived


@pytest.mark.parametrize("enabled", [True, False])
def test_api_access_toggle(client, enabled):
    _make_dashboard("toggle-api")
    if not enabled:
        client.post("/api/dashboards/toggle-api/api-access", json={"enabled": True}, headers=_h())
    r = client.post("/api/dashboards/toggle-api/api-access", json={"enabled": enabled}, headers=_h())
    assert r.status_code == 200
    assert r.json() == {"slug": "toggle-api", "has_api_access": enabled}
    with get_db() as session:
        d = session.scalar(select(Dashboard).where(Dashboard.slug == "toggle-api"))
        assert d.has_api_access is enabled


def test_archive_unknown_slug_404(client):
    r = client.post("/api/dashboards/ghost/archive", json={"archived": True}, headers=_h())
    assert r.status_code == 404


def test_toggle_bad_slug_422(client):
    r = client.post("/api/dashboards/Bad.Slug/archive", json={"archived": True}, headers=_h())
    assert r.status_code == 422


def test_rechercher_omits_dashboards(client):
    _make_dashboard("rech-omit", title="ZZZ-Unique-Dashboard-Title")
    r = client.get("/rechercher?show=apps", headers=_h())
    assert r.status_code == 200
    assert "ZZZ-Unique-Dashboard-Title" not in r.text
    r2 = client.get("/rechercher", headers=_h())
    assert r2.status_code == 200
    assert "ZZZ-Unique-Dashboard-Title" not in r2.text


def test_rename_dashboard(client):
    _make_dashboard("rename-me", title="Old")
    r = client.post("/api/dashboards/rename-me/rename", json={"title": "Brand New"}, headers=_h())
    assert r.status_code == 200
    assert r.json() == {"slug": "rename-me", "title": "Brand New"}
    with get_db() as session:
        d = session.scalar(select(Dashboard).where(Dashboard.slug == "rename-me"))
        assert d.title == "Brand New"


def test_rename_empty_title_400(client):
    _make_dashboard("rename-empty")
    r = client.post("/api/dashboards/rename-empty/rename", json={"title": "  "}, headers=_h())
    assert r.status_code == 400


def test_rename_unknown_slug_404(client):
    r = client.post("/api/dashboards/ghost/rename", json={"title": "X"}, headers=_h())
    assert r.status_code == 404


def test_listing_shows_cron_status(client):
    _make_dashboard("croned")
    now = datetime.now(timezone.utc)
    with get_db() as session:
        d = session.scalar(select(Dashboard).where(Dashboard.slug == "croned"))
        d.has_cron = True
        session.add(CronRun(app_slug="croned", started_at=now, status="success", trigger="scheduled"))
    r = client.get("/dashboards", headers=_h())
    assert r.status_code == 200
    assert 'title="success"' in r.text


def test_detail_hides_api_access_toggle(client):
    _make_dashboard("no-api-toggle")
    r = client.get("/dashboards/no-api-toggle/edit", headers=_h())
    assert r.status_code == 200
    assert "apiAccessToggle" not in r.text
    assert "Accès API" not in r.text
