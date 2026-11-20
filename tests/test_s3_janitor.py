"""Le balayeur du bucket : ce qu'il efface, ce qu'il ne touche jamais, et ce qu'il en dit sur Slack."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from botocore.exceptions import ClientError

from web import s3, s3_janitor
from web.db import get_db
from web.environment import Environment
from web.models import Dashboard, DashboardPublication, UploadedFile

NOW = datetime(2026, 11, 16, tzinfo=timezone.utc)
CONVERSATION = "0b6f3c1e-5d2a-4c8e-9f1a-2b3c4d5e6f70"


def make_dashboard(session, slug):
    session.add(
        Dashboard(
            slug=slug,
            title="t",
            description="d",
            website="emplois",
            category="c",
            first_author_email="alice@x",
            is_archived=False,
            has_api_access=False,
            has_cron=False,
            has_persistence=False,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    session.flush()


def make_publication(session, slug, publication_id, unpublished_at):
    session.add(
        DashboardPublication(
            dashboard_slug=slug,
            publication_id=publication_id,
            environment="production",
            published_by="bob@x",
            published_at=NOW - timedelta(days=90),
            unpublished_at=unpublished_at,
        )
    )


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
def test_live_and_recently_retired_publications_and_attached_uploads_are_referenced():
    run_id = uuid.uuid4().hex[:8]
    with get_db() as session:
        make_dashboard(session, f"janitor-{run_id}")
        for publication_id, unpublished_at in (
            (f"live-{run_id}", None),
            (f"recent-{run_id}", NOW - timedelta(days=10)),
            (f"old-{run_id}", NOW - timedelta(days=40)),
        ):
            make_publication(session, f"janitor-{run_id}", publication_id, unpublished_at)
        session.add(
            UploadedFile(
                original_filename="f.csv",
                stored_filename=f"{CONVERSATION}/upload-{run_id}.csv",
                storage_path="/data/uploads/f.csv",
                file_size=1,
                sha256_hash="h",
                created_at=NOW,
            )
        )

    publications, uploads = s3_janitor.referenced(NOW)

    assert {f"live-{run_id}", f"recent-{run_id}"} <= publications
    assert f"old-{run_id}" not in publications
    assert f"{CONVERSATION}/upload-{run_id}.csv" in uploads


def entry(path: str, days_old: int, size: int = 1000) -> dict:
    return {"path": path, "size": size, "last_modified": NOW - timedelta(days=days_old), "etag": "e"}


def bucket(mocker, *, publications=(), uploads=(), interactive=(), deleted=True):
    listings = {s3.publications: list(publications), s3.uploads: list(uploads), s3.interactive: list(interactive)}
    for store, files in listings.items():
        mocker.patch.object(store, "list_files", return_value=files)
    return {store: mocker.patch.object(store, "delete", return_value=deleted) for store in listings}


@pytest.mark.parametrize(
    ("listing", "garbage"),
    [
        ({"publications": [entry("tdb/old-id/index.html", 40)]}, ["publications/tdb/old-id/index.html"]),
        ({"publications": [entry("tdb/old-id/data/rows.json", 40)]}, ["publications/tdb/old-id/data/rows.json"]),
        ({"publications": [entry("tdb/live-id/index.html", 400)]}, []),
        ({"publications": [entry("tdb/old-id/index.html", 20)]}, []),
        ({"publications": [entry("tdb/stray.html", 400)]}, []),
        ({"uploads": [entry(f"{CONVERSATION}/gone.csv", 40)]}, [f"uploads/{CONVERSATION}/gone.csv"]),
        ({"uploads": [entry("20260101_abc_gone.csv", 40)]}, ["uploads/20260101_abc_gone.csv"]),
        ({"uploads": [entry(f"{CONVERSATION}/kept.csv", 400)]}, []),
        ({"uploads": [entry("20260101_abc_kept.csv", 400)]}, []),
        ({"uploads": [entry(f"{CONVERSATION}/gone.csv", 20)]}, []),
        (
            {"interactive": [entry("tdb/app.js.tmp.10939.db92350fc2ce", 40)]},
            ["interactive/tdb/app.js.tmp.10939.db92350fc2ce"],
        ),
        (
            {"interactive": [entry("tdb/__pycache__/cron.cpython-314.pyc", 40)]},
            ["interactive/tdb/__pycache__/cron.cpython-314.pyc"],
        ),
        ({"interactive": [entry("tdb/__pycache__/cron.cpython-314.pyc", 20)]}, []),
        ({"interactive": [entry("tdb/index.html", 400)]}, []),
        ({"interactive": [entry("export.csv", 400)]}, []),
    ],
)
def test_only_what_nothing_references_or_touched_for_a_month_is_garbage(mocker, listing, garbage):
    bucket(mocker, **listing)

    found = s3_janitor.find_garbage({"live-id"}, {f"{CONVERSATION}/kept.csv", "20260101_abc_kept.csv"}, NOW)

    assert [store.key(e["path"]) for store, e in found] == garbage


@pytest.mark.parametrize(
    ("publications", "uploads"),
    [(set(), {"other.csv"}), ({"other-id"}, set())],
    ids=["no-publication", "no-upload"],
)
def test_a_prefix_the_database_references_nothing_in_is_left_alone(mocker, publications, uploads):
    bucket(mocker, publications=[entry("tdb/old-id/index.html", 400)], uploads=[entry("gone.csv", 400)])
    swept, untouched = (s3.publications, s3.uploads) if publications else (s3.uploads, s3.publications)

    found = s3_janitor.find_garbage(publications, uploads, NOW)

    untouched.list_files.assert_not_called()
    assert [store for store, _ in found] == [swept]


def sweep(mocker, monkeypatch, *, delete, env=Environment.PROD, deleted=True, publications=(), uploads=(), backup=None):
    monkeypatch.setattr("web.s3_janitor.config.ENV", env)
    referenced = mocker.patch("web.s3_janitor.referenced", return_value=({"live-id"}, {"kept.csv"}))
    mocker.patch("web.s3_janitor.check_mirror_manifest", side_effect=backup)
    deletes = bucket(mocker, publications=publications, uploads=uploads, deleted=deleted)
    slack = mocker.patch("web.s3_janitor.alerts.notify_alert_channel", return_value="1700000000.000100")
    s3_janitor.run(delete=delete)
    return referenced, deletes, slack


@pytest.mark.parametrize(
    ("delete", "deletions", "summary"),
    [
        (False, 0, ":broom: Balayeur aurait effacé 2 fichiers (0,0 Mo) — dry run, rien n'a été supprimé"),
        (True, 2, ":broom: Balayeur a effacé 2 fichiers (0,0 Mo)"),
    ],
    ids=["dry-run", "wet-run"],
)
def test_it_deletes_only_when_told_and_says_which_run_it_was(mocker, monkeypatch, delete, deletions, summary):
    _, deletes, slack = sweep(
        mocker,
        monkeypatch,
        delete=delete,
        publications=[entry("tdb/old-id/index.html", 40), entry("tdb/old-id/data.json", 40)],
    )

    assert deletes[s3.publications].call_count == deletions
    assert slack.call_args_list[0].args == (summary,)


@pytest.mark.parametrize("env", [Environment.DEV, Environment.REVIEW, Environment.STAGING])
def test_nothing_is_read_deleted_or_posted_outside_production(mocker, monkeypatch, env):
    referenced, deletes, slack = sweep(
        mocker, monkeypatch, delete=True, env=env, publications=[entry("tdb/old-id/index.html", 40)]
    )

    referenced.assert_not_called()
    assert not any(d.called for d in deletes.values())
    slack.assert_not_called()


def test_a_deletion_s3_refuses_is_not_counted_and_is_reported(mocker, monkeypatch):
    _, _, slack = sweep(mocker, monkeypatch, delete=True, deleted=False, uploads=[entry("gone.csv", 40)])

    assert slack.call_args_list[0].args == (
        ":broom: Balayeur a effacé 0 fichier (0,0 Mo) ; S3 a refusé 1 suppression, voir les logs",
    )


def test_the_thread_counts_files_per_snapshot_and_per_conversation_and_never_names_an_upload(
    mocker, monkeypatch, caplog
):
    caplog.set_level("INFO", logger="web.s3_janitor")
    _, _, slack = sweep(
        mocker,
        monkeypatch,
        delete=True,
        publications=[entry("tdb/old-id/index.html", 40), entry("tdb/old-id/data.json", 40)],
        uploads=[
            entry(f"{CONVERSATION}/20260101_abc_CV_Prenom_Nom.pdf", 40),
            entry(f"{CONVERSATION}/20260101_def_lettre.pdf", 40),
            entry("20250101_ghi_CV_Autre_Nom.pdf", 40),
        ],
    )

    reply = slack.call_args_list[1]
    assert reply.kwargs == {"thread_ts": "1700000000.000100"}
    assert reply.args == (
        f"```\npublications/tdb/old-id/ (2 fichiers)\nuploads/ (1 fichier)\nuploads/{CONVERSATION}/ (2 fichiers)\n```",
    )
    assert "Nom" not in str(slack.call_args_list) + caplog.text


def test_a_long_list_is_split_across_replies(mocker, monkeypatch):
    publications = [entry(f"tdb-{'x' * 60}/{n:04d}/index.html", 40) for n in range(200)]

    _, _, slack = sweep(mocker, monkeypatch, delete=True, publications=publications)

    replies = [call.args[0] for call in slack.call_args_list[1:]]
    assert len(replies) > 1
    assert all(len(reply) < 3100 for reply in replies)
    assert sum(reply.count("publications/") for reply in replies) == 200


@pytest.mark.parametrize(
    "backup",
    [RuntimeError("Mirror manifest missing"), ClientError({"Error": {"Code": "AccessDenied"}}, "GetObject")],
    ids=["missing-or-failed", "unreadable"],
)
def test_without_todays_backup_it_only_lists(mocker, monkeypatch, backup):
    _, deletes, slack = sweep(
        mocker, monkeypatch, delete=True, backup=backup, publications=[entry("tdb/old-id/index.html", 40)]
    )

    deletes[s3.publications].assert_not_called()
    assert slack.call_args_list[0].args == (
        ":broom: Balayeur aurait effacé 1 fichier (0,0 Mo) — dry run faute de sauvegarde complète aujourd'hui,"
        " rien n'a été supprimé",
    )


def test_the_list_is_logged_before_anything_is_deleted(mocker, monkeypatch, caplog):
    caplog.set_level("INFO", logger="web.s3_janitor")
    logged_before = []
    monkeypatch.setattr("web.s3_janitor.config.ENV", Environment.PROD)
    mocker.patch("web.s3_janitor.referenced", return_value=({"live-id"}, {"kept.csv"}))
    mocker.patch("web.s3_janitor.check_mirror_manifest")
    mocker.patch("web.s3_janitor.alerts.notify_alert_channel", return_value=None)
    bucket(mocker, publications=[entry("tdb/old-id/index.html", 40)])
    mocker.patch.object(s3.publications, "delete", side_effect=lambda path: logged_before.append(caplog.text))

    s3_janitor.run(delete=True)

    assert "publications/tdb/old-id/ (1 fichier)" in logged_before[0]


@pytest.mark.parametrize("thread", [None, "1700000000.000100"], ids=["slack-unconfigured", "nothing-swept"])
def test_no_reply_without_a_thread_or_without_files(mocker, monkeypatch, thread):
    monkeypatch.setattr("web.s3_janitor.config.ENV", Environment.PROD)
    mocker.patch("web.s3_janitor.referenced", return_value=({"live-id"}, {"kept.csv"}))
    mocker.patch("web.s3_janitor.check_mirror_manifest")
    bucket(mocker, uploads=[entry("gone.csv", 40)] if thread is None else [])
    slack = mocker.patch("web.s3_janitor.alerts.notify_alert_channel", return_value=thread)

    s3_janitor.run(delete=True)

    assert slack.call_count == 1
