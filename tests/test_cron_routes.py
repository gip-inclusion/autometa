"""Tests for cron route slug validation — guards against path-injection in downstream tempfile/S3 keys."""

from datetime import datetime, timezone

import pytest

from web import cron
from web.db import get_db
from web.models import Dashboard, DashboardPublication


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/api/cron/{slug}/run"),
        ("post", "/api/cron/{slug}/toggle"),
        ("get", "/api/cron/{slug}/script"),
        ("get", "/api/cron/{slug}/logs"),
    ],
)
@pytest.mark.parametrize(
    "bad_slug",
    [
        "foo..bar",
        "UPPER",
        "with.dot",
        "with$dollar",
        "with%20encoded",
        "a" * 101,
    ],
)
def test_invalid_slug_rejected(client, method, path, bad_slug):
    response = getattr(client, method)(path.format(slug=bad_slug))
    assert response.status_code == 422


def test_valid_slug_reaches_handler(client, mocker):
    mocker.patch("web.routes.cron.find_task", return_value=None)
    response = client.get("/api/cron/check-s3-backups/script")
    assert response.status_code == 404
    assert response.json() == {"error": "Task not found"}


def test_view_script_s3_task(client, mocker):
    mocker.patch("web.routes.cron.find_task", return_value={"slug": "x", "source": "s3", "cron_path": "x/cron.py"})
    mocker.patch("web.routes.cron.read_cron_script", return_value="print('hi')")
    response = client.get("/api/cron/x/script")
    assert response.status_code == 200
    assert "print('hi')" in response.text


def test_view_script_missing_returns_404_not_500(client, mocker):
    mocker.patch("web.routes.cron.find_task", return_value={"slug": "x", "source": "s3", "cron_path": "x/cron.py"})
    mocker.patch("web.routes.cron.read_cron_script", return_value=None)
    response = client.get("/api/cron/x/script")
    assert response.status_code == 404


def test_read_cron_script_local(tmp_path):
    script = tmp_path / "cron.py"
    script.write_text("print('local')")
    assert cron.read_cron_script({"cron_path": str(script)}) == "print('local')"


def test_read_cron_script_s3(mocker):
    mocker.patch("web.cron.s3.interactive.download", return_value=b"print('s3')")
    assert cron.read_cron_script({"source": "s3", "cron_path": "x/cron.py"}) == "print('s3')"


def _make_dashboard_and_pub(slug, *, pubs=()):
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
                has_api_access=False,
                has_cron=True,
                has_persistence=False,
                created_at=now,
                updated_at=now,
            )
        )
        for pub_id, snapshot_has_cron, unpublished, paused in pubs:
            session.add(
                DashboardPublication(
                    dashboard_slug=slug,
                    publication_id=pub_id,
                    environment="staging",
                    published_by="bob@x",
                    published_at=now,
                    snapshot_has_cron=snapshot_has_cron,
                    unpublished_at=now if unpublished else None,
                    refresh_paused_at=now if paused else None,
                )
            )


def _fake_run(slug, trigger):
    return {"slug": slug, "status": "success", "duration_ms": 10, "output": "ok"}


def test_run_endpoint_fans_out_to_active_cron_publications(client, mocker):
    _make_dashboard_and_pub(
        "fanout",
        pubs=[
            ("pubapa", True, False, False),
            ("pubapb", False, False, False),
        ],
    )
    mocker.patch(
        "web.routes.cron.find_task",
        return_value={"slug": "fanout", "source": "s3", "title": "Fanout", "cron_path": "fanout/cron.py"},
    )
    run = mocker.patch("web.routes.cron.run_cron_task", side_effect=_fake_run)

    r = client.post("/api/cron/fanout/run")
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "fanout"
    assert run.call_args_list[0].args == ("fanout",)
    fanned_slugs = [call.args[0] for call in run.call_args_list[1:]]
    assert fanned_slugs == ["fanout-pubapa"]
    assert body["publications"] == [{"slug": "fanout-pubapa", "status": "success", "duration_ms": 10}]


def test_run_endpoint_skips_paused_and_unpublished(client, mocker):
    _make_dashboard_and_pub(
        "skipper",
        pubs=[
            ("pubska", True, False, True),
            ("pubskb", True, True, False),
            ("pubskc", True, False, False),
        ],
    )
    mocker.patch(
        "web.routes.cron.find_task",
        return_value={"slug": "skipper", "source": "s3", "title": "Skipper", "cron_path": "skipper/cron.py"},
    )
    mocker.patch("web.routes.cron.run_cron_task", side_effect=_fake_run)

    r = client.post("/api/cron/skipper/run")
    assert r.status_code == 200
    body = r.json()
    fanned = [p["slug"] for p in body["publications"]]
    assert fanned == ["skipper-pubskc"]


def test_run_endpoint_fans_out_even_when_working_copy_fails(client, mocker):
    _make_dashboard_and_pub(
        "failover",
        pubs=[("pubfaa", True, False, False)],
    )
    mocker.patch(
        "web.routes.cron.find_task",
        return_value={"slug": "failover", "source": "s3", "title": "Failover", "cron_path": "failover/cron.py"},
    )

    def fake_run(slug, trigger):
        if slug == "failover":
            return {"slug": slug, "status": "failure", "duration_ms": 5, "output": "boom"}
        return {"slug": slug, "status": "success", "duration_ms": 10, "output": "ok"}

    mocker.patch("web.routes.cron.run_cron_task", side_effect=fake_run)

    r = client.post("/api/cron/failover/run")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "failure"
    assert body["publications"] == [{"slug": "failover-pubfaa", "status": "success", "duration_ms": 10}]


def test_run_endpoint_no_fanout_for_publication_composite(client, mocker):
    """Triggering a publication directly (composite slug) runs only that publication."""
    _make_dashboard_and_pub("composite", pubs=[("pubcoa", True, False, False)])
    mocker.patch(
        "web.routes.cron.find_task",
        return_value={
            "slug": "composite-pubcoa",
            "source": "s3-publication",
            "title": "Composite",
            "cron_path": "composite/pubcoa/cron.py",
            "publication_id": "pubcoa",
            "dashboard_slug": "composite",
        },
    )
    run = mocker.patch("web.routes.cron.run_cron_task", side_effect=_fake_run)

    r = client.post("/api/cron/composite-pubcoa/run")
    assert r.status_code == 200
    body = r.json()
    assert run.call_count == 1
    assert body["publications"] == []
