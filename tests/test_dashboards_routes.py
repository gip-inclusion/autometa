from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from web.config import ADMIN_USERS
from web.database import store
from web.db import get_db
from web.models import CronRun, Dashboard, DashboardPublication

ADMIN = ADMIN_USERS[0]


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


def test_featured_only_shown_on_latest(client):
    _make_dashboard("feat-latest-only", author="alice@x")
    store.pin_item("app", "feat-latest-only", "Feat")
    assert "À la une" in client.get("/dashboards?view=latest", headers=_h()).text
    assert "À la une" not in client.get("/dashboards?view=mine", headers=_h("other@x")).text
    assert "À la une" not in client.get("/dashboards?view=archived", headers=_h()).text


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


def test_listing_groups_by_time_and_has_icons(client):
    _make_dashboard("grouped-one")
    r = client.get("/dashboards", headers=_h())
    assert r.status_code == 200
    assert "conv-group-header" in r.text
    assert "conv-item-icon" in r.text


def test_detail_hides_api_access_toggle(client):
    _make_dashboard("no-api-toggle")
    r = client.get("/dashboards/no-api-toggle/edit", headers=_h())
    assert r.status_code == 200
    assert "apiAccessToggle" not in r.text
    assert "Accès API" not in r.text


def test_publish_endpoint_creates_publication(client, mocker):
    _make_dashboard("route-pub")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    mocker.patch("web.publications.s3.delete_prefix", return_value=0)
    r = client.post("/api/dashboards/route-pub/publish", json={"environment": "staging"}, headers=_h())
    assert r.status_code == 200
    assert r.json()["environment"] == "staging"


def test_publish_endpoint_blocked_returns_409(client, mocker):
    _make_dashboard("route-pub-api")
    with get_db() as session:
        d = session.scalar(select(Dashboard).where(Dashboard.slug == "route-pub-api"))
        d.has_api_access = True
    r = client.post("/api/dashboards/route-pub-api/publish", json={"environment": "staging"}, headers=_h())
    assert r.status_code == 409


def test_publish_endpoint_bad_environment_400(client):
    _make_dashboard("route-pub-bad")
    r = client.post("/api/dashboards/route-pub-bad/publish", json={"environment": "wat"}, headers=_h())
    assert r.status_code == 400


def test_unpublish_endpoint(client, mocker):
    _make_dashboard("route-unp")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    mocker.patch("web.publications.s3.delete_prefix", return_value=1)
    pub = client.post("/api/dashboards/route-unp/publish", json={"environment": "staging"}, headers=_h()).json()
    r = client.post(f"/api/publications/{pub['publication_id']}/unpublish", headers=_h())
    assert r.status_code == 200


def test_unpublish_endpoint_bad_id_422(client):
    r = client.post("/api/publications/BAD!/unpublish", headers=_h())
    assert r.status_code == 422


def test_detail_shows_publish_buttons(client):
    _make_dashboard("pub-buttons")
    r = client.get("/dashboards/pub-buttons/edit", headers=_h())
    assert r.status_code == 200
    assert 'data-action="publish"' in r.text
    assert "Publier une nouvelle version en staging" in r.text
    assert "Publier en production" in r.text
    assert "Re-publier" not in r.text


def test_detail_slug_links_to_interactive_app(client):
    _make_dashboard("link-slug")
    r = client.get("/dashboards/link-slug/edit", headers=_h())
    assert r.status_code == 200
    assert 'href="/interactive/link-slug/"' in r.text
    assert "ri-external-link-line" in r.text


def test_detail_production_button_says_republier_when_prod_exists(client, mocker):
    _make_dashboard("republier")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    client.post("/api/dashboards/republier/publish", json={"environment": "production"}, headers=_h())
    r = client.get("/dashboards/republier/edit", headers=_h())
    assert r.status_code == 200
    assert "Re-publier en production" in r.text


def test_detail_production_button_stays_publier_when_only_staging_exists(client, mocker):
    _make_dashboard("only-staging")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    client.post("/api/dashboards/only-staging/publish", json={"environment": "staging"}, headers=_h())
    r = client.get("/dashboards/only-staging/edit", headers=_h())
    assert r.status_code == 200
    assert "Re-publier" not in r.text
    assert "Publier en production" in r.text


def test_detail_blocks_publish_for_query_api(client):
    _make_dashboard("pub-blocked")
    with get_db() as session:
        d = session.scalar(select(Dashboard).where(Dashboard.slug == "pub-blocked"))
        d.has_api_access = True
    r = client.get("/dashboards/pub-blocked/edit", headers=_h())
    assert r.status_code == 200
    assert 'data-action="publish"' not in r.text
    assert "Publication indisponible" in r.text


def test_detail_lists_publications(client, mocker):
    _make_dashboard("detail-lists")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    mocker.patch("web.publications.s3.delete_prefix", return_value=0)
    client.post("/api/dashboards/detail-lists/publish", json={"environment": "staging"}, headers=_h())
    r = client.get("/dashboards/detail-lists/edit", headers=_h())
    assert r.status_code == 200
    assert "Dépublier" in r.text


def test_archiving_unpublishes_all(client, mocker):
    _make_dashboard("arch-unp")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    delete = mocker.patch("web.publications.s3.delete_prefix", return_value=1)
    client.post("/api/dashboards/arch-unp/publish", json={"environment": "staging"}, headers=_h())
    r = client.post("/api/dashboards/arch-unp/archive", json={"archived": True}, headers=_h())
    assert r.status_code == 200
    detail = client.get("/dashboards/arch-unp/edit", headers=_h())
    assert "Dépublier" not in detail.text
    assert delete.called


def test_refresh_pause_endpoint_pauses_and_resumes(client, mocker):
    _make_dashboard("route-pause")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    mocker.patch("web.publications.s3.interactive.exists", return_value=True)
    pub = client.post(
        "/api/dashboards/route-pause/publish",
        json={"environment": "staging"},
        headers=_h(),
    ).json()
    pid = pub["publication_id"]

    r = client.post(f"/api/publications/{pid}/refresh-pause", headers=_h())
    assert r.status_code == 200
    assert r.json() == {"ok": True, "paused": True}

    r = client.post(f"/api/publications/{pid}/refresh-resume", headers=_h())
    assert r.status_code == 200
    assert r.json() == {"ok": True, "paused": False}


def test_refresh_pause_endpoint_bad_id_422(client):
    r = client.post("/api/publications/BAD!/refresh-pause", headers=_h())
    assert r.status_code == 422


def test_refresh_pause_endpoint_unknown_404(client):
    r = client.post("/api/publications/abcdef/refresh-pause", headers=_h())
    assert r.status_code == 404


def test_refresh_pause_endpoint_idempotent_200(client, mocker):
    _make_dashboard("route-pause-idem")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    mocker.patch("web.publications.s3.interactive.exists", return_value=True)
    pub = client.post(
        "/api/dashboards/route-pause-idem/publish",
        json={"environment": "staging"},
        headers=_h(),
    ).json()
    pid = pub["publication_id"]

    client.post(f"/api/publications/{pid}/refresh-pause", headers=_h())
    r = client.post(f"/api/publications/{pid}/refresh-pause", headers=_h())
    assert r.status_code == 200
    assert r.json() == {"ok": True, "paused": True}


def test_detail_drift_hint_shown_when_dashboard_newer(client, mocker):
    _make_dashboard("drift-yes")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    mocker.patch("web.publications.s3.interactive.exists", return_value=False)
    client.post("/api/dashboards/drift-yes/publish", json={"environment": "staging"}, headers=_h())
    # Bump dashboards.updated_at to *after* the publication's published_at.
    with get_db() as session:
        d = session.scalar(select(Dashboard).where(Dashboard.slug == "drift-yes"))
        d.updated_at = datetime.now(timezone.utc) + timedelta(hours=1)
    r = client.get("/dashboards/drift-yes/edit", headers=_h())
    assert r.status_code == 200
    assert "modifié depuis la dernière publication" in r.text


def test_detail_drift_hint_hidden_when_not_drifted(client, mocker):
    _make_dashboard("drift-no")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    mocker.patch("web.publications.s3.interactive.exists", return_value=False)
    client.post("/api/dashboards/drift-no/publish", json={"environment": "staging"}, headers=_h())
    r = client.get("/dashboards/drift-no/edit", headers=_h())
    assert r.status_code == 200
    assert "modifié depuis la dernière publication" not in r.text


def test_detail_shows_suspendre_when_snapshot_has_cron(client, mocker):
    _make_dashboard("ui-suspend")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    mocker.patch("web.publications.s3.interactive.exists", return_value=True)
    client.post("/api/dashboards/ui-suspend/publish", json={"environment": "staging"}, headers=_h())
    r = client.get("/dashboards/ui-suspend/edit", headers=_h())
    assert r.status_code == 200
    assert "Suspendre" in r.text
    assert "Données rafraîchies" in r.text


def test_detail_shows_reprendre_when_paused(client, mocker):
    _make_dashboard("ui-resume")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    mocker.patch("web.publications.s3.interactive.exists", return_value=True)
    pub = client.post(
        "/api/dashboards/ui-resume/publish",
        json={"environment": "staging"},
        headers=_h(),
    ).json()
    client.post(f"/api/publications/{pub['publication_id']}/refresh-pause", headers=_h())
    r = client.get("/dashboards/ui-resume/edit", headers=_h())
    assert r.status_code == 200
    assert "Reprendre" in r.text
    assert "Données figées" in r.text


def test_detail_no_refresh_ui_when_snapshot_lacks_cron(client, mocker):
    _make_dashboard("ui-nocron")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    mocker.patch("web.publications.s3.interactive.exists", return_value=False)
    client.post("/api/dashboards/ui-nocron/publish", json={"environment": "staging"}, headers=_h())
    r = client.get("/dashboards/ui-nocron/edit", headers=_h())
    assert r.status_code == 200
    assert "Suspendre" not in r.text
    assert "Reprendre" not in r.text
    assert "Données rafraîchies" not in r.text


def test_detail_cron_card_shows_status_badge_and_history_button(client):
    _make_dashboard("cron-detail")
    now = datetime.now(timezone.utc)
    with get_db() as session:
        d = session.scalar(select(Dashboard).where(Dashboard.slug == "cron-detail"))
        d.has_cron = True
        session.add(
            CronRun(
                app_slug="cron-detail",
                started_at=now,
                finished_at=now,
                status="success",
                duration_ms=1234,
                trigger="manual",
            )
        )
    r = client.get("/dashboards/cron-detail/edit", headers=_h())
    assert r.status_code == 200
    assert 'data-action="cron-history" data-slug="cron-detail"' in r.text
    assert "1.2s" in r.text
    assert "(manual," in r.text
    assert "bg-success" in r.text


def test_detail_cron_card_shows_next_run_estimate(client):
    _make_dashboard("next-run")
    with get_db() as session:
        d = session.scalar(select(Dashboard).where(Dashboard.slug == "next-run"))
        d.has_cron = True
    r = client.get("/dashboards/next-run/edit", headers=_h())
    assert r.status_code == 200
    assert "Prochaine exécution" in r.text


def test_detail_cron_card_no_next_run_when_no_cron(client):
    _make_dashboard("no-cron")
    r = client.get("/dashboards/no-cron/edit", headers=_h())
    assert r.status_code == 200
    assert "Prochaine exécution" not in r.text


def test_detail_publication_uses_c_box_results_structure(client, mocker):
    _make_dashboard("c-box-pub")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    mocker.patch("web.publications.s3.interactive.exists", return_value=True)
    client.post("/api/dashboards/c-box-pub/publish", json={"environment": "staging"}, headers=_h())
    r = client.get("/dashboards/c-box-pub/edit", headers=_h())
    assert r.status_code == 200
    assert 'class="c-box c-box--results' in r.text
    assert 'class="c-box--results__header"' in r.text
    assert 'class="c-box--results__body"' in r.text
    assert "Rafraîchir les données" in r.text


def test_detail_publication_row_shows_run_and_history_when_snapshot_has_cron(client, mocker):
    _make_dashboard("pub-history")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    mocker.patch("web.publications.s3.interactive.exists", return_value=True)
    pub = client.post(
        "/api/dashboards/pub-history/publish",
        json={"environment": "staging"},
        headers=_h(),
    ).json()
    r = client.get("/dashboards/pub-history/edit", headers=_h())
    assert r.status_code == 200
    assert f'data-action="pub-history" data-slug="pub-history-{pub["publication_id"]}"' in r.text
    assert f'data-action="pub-run" data-slug="pub-history-{pub["publication_id"]}"' in r.text


def test_detail_publication_row_omits_run_and_history_when_no_snapshot_cron(client, mocker):
    _make_dashboard("pub-no-history")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    mocker.patch("web.publications.s3.interactive.exists", return_value=False)
    client.post(
        "/api/dashboards/pub-no-history/publish",
        json={"environment": "staging"},
        headers=_h(),
    )
    r = client.get("/dashboards/pub-no-history/edit", headers=_h())
    assert r.status_code == 200
    assert 'data-action="pub-history" data-slug=' not in r.text
    assert 'data-action="pub-run" data-slug=' not in r.text


def _mock_publish_s3(mocker):
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    mocker.patch("web.publications.s3.delete_prefix", return_value=1)
    mocker.patch("web.publications.s3.interactive.exists", return_value=True)


def test_published_view_lists_active_publications(client, mocker):
    _mock_publish_s3(mocker)
    _make_dashboard("pubv-listed", title="TDB Publié")
    _make_dashboard("pubv-unpublished", title="TDB Non Publié")
    client.post("/api/dashboards/pubv-listed/publish", json={"environment": "staging"}, headers=_h())
    r = client.get("/dashboards?view=published", headers=_h())
    assert r.status_code == 200
    assert "TDB Publié" in r.text
    assert "TDB Non Publié" not in r.text
    assert "env-pill-staging" in r.text
    assert 'href="/dashboards/pubv-listed/edit"' in r.text


def test_published_view_groups_publications_prod_first(client, mocker):
    _mock_publish_s3(mocker)
    _make_dashboard("pubv-multi", title="TDB Multi")
    client.post("/api/dashboards/pubv-multi/publish", json={"environment": "staging"}, headers=_h())
    client.post("/api/dashboards/pubv-multi/publish", json={"environment": "production"}, headers=_h())
    r = client.get("/dashboards?view=published", headers=_h())
    assert r.status_code == 200
    assert r.text.count("env-pill-prod") == 1
    assert r.text.count("env-pill-staging") == 1
    assert r.text.index("env-pill-prod") < r.text.index("env-pill-staging")


def test_published_view_empty_state(client):
    r = client.get("/dashboards?view=published", headers=_h())
    assert r.status_code == 200
    assert "Aucune publication active" in r.text


def test_published_view_excludes_archived_dashboards(client, mocker):
    _mock_publish_s3(mocker)
    _make_dashboard("pubv-arch", title="TDB Archivé")
    client.post("/api/dashboards/pubv-arch/publish", json={"environment": "staging"}, headers=_h())
    client.post("/api/dashboards/pubv-arch/archive", json={"archived": True}, headers=_h())
    r = client.get("/dashboards?view=published", headers=_h())
    assert r.status_code == 200
    assert "TDB Archivé" not in r.text


def test_published_view_button_in_sidebar(client):
    r = client.get("/dashboards", headers=_h())
    assert r.status_code == 200
    assert 'data-view="published"' in r.text


def test_detail_shows_failure_suffix_when_last_refresh_failed(client, mocker):
    _make_dashboard("ui-failure")
    mocker.patch("web.publications.s3.copy_prefix", return_value=1)
    mocker.patch("web.publications.s3.sync_prefix", return_value=1)
    mocker.patch("web.publications.s3.interactive.exists", return_value=True)
    pub = client.post(
        "/api/dashboards/ui-failure/publish",
        json={"environment": "staging"},
        headers=_h(),
    ).json()
    with get_db() as session:
        p = session.scalar(
            select(DashboardPublication).where(DashboardPublication.publication_id == pub["publication_id"])
        )
        p.last_refresh_status = "failure"
    r = client.get("/dashboards/ui-failure/edit", headers=_h())
    assert r.status_code == 200
    assert "rafraîchissement en échec" in r.text
