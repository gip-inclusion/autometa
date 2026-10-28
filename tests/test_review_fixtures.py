"""Le jeu de démonstration des review apps : ce qu'il crée, qu'il converge à chaque déploiement, et sa purge."""

import importlib.util
import json
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, func, select, update

from lib import review_fixtures
from web import config, s3
from web.db import get_db
from web.db import test_transaction as _test_tx
from web.environment import Environment
from web.models import (
    Conversation,
    CronRun,
    Dashboard,
    DashboardPublication,
    Message,
    PinnedItem,
    Report,
    UserFavorite,
)

ADMIN_CONVERSATION = "d3e00000-0000-4000-8000-000000000001"
GIGA_CONVERSATION = "d3e00000-0000-4000-8000-000000000002"
SOURCE_CONVERSATION = "d3e00000-0000-4000-8000-000000000003"
CLONE_CONVERSATION = "d3e00000-0000-4000-8000-000000000004"
FLAGGED_CONVERSATION = "d3e00000-0000-4000-8000-000000000005"
FIXTURES = review_fixtures.load()
CONVERSATIONS = [spec["id"] for spec in FIXTURES["conversations"]]
SLUGS = [spec["slug"] for spec in FIXTURES["dashboards"]]


@pytest.fixture
def seeded(_db, tmp_path, monkeypatch, mocker):
    monkeypatch.setattr(config, "INTERACTIVE_DIR", tmp_path)
    mocks = SimpleNamespace(
        upload=mocker.patch.object(s3.interactive, "upload", return_value=True),
        copy_prefix=mocker.patch.object(s3, "copy_prefix", return_value=1),
        sync_prefix=mocker.patch.object(s3, "sync_prefix", return_value=1),
    )
    with _test_tx():
        review_fixtures.seed()
        yield mocks


def messages(conversation_id):
    with get_db() as session:
        return session.execute(
            select(Message.content, Message.timestamp)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id)
        ).all()


def counts():
    with get_db() as session:
        return {
            model.__tablename__: session.scalar(select(func.count()).select_from(model))
            for model in (Conversation, Message, Report, Dashboard, CronRun, DashboardPublication)
        }


def load_cron():
    spec = importlib.util.spec_from_file_location("demo_cron", review_fixtures.FIXTURES_DIR / "cron.py")
    cron = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cron)
    return cron


@pytest.mark.integration
def test_giga_conversation_holds_thousands_of_messages(seeded):
    assert len(messages(GIGA_CONVERSATION)) >= 6000


@pytest.mark.parametrize(("env", "admin"), [("review", True), ("staging", False)])
def test_demo_admin_is_an_admin_only_on_review_apps(env, admin, monkeypatch):
    demo_admin = next(spec["owner"] for spec in FIXTURES["conversations"] if spec["id"] == ADMIN_CONVERSATION)
    monkeypatch.setenv("AUTOMETA_ENV", env)
    try:
        assert (demo_admin in importlib.reload(config).ADMIN_USERS) is admin
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_every_clone_follows_its_source():
    """Le seed copie les messages de la source au moment du clone : elle doit déjà exister."""
    order = [spec["id"] for spec in FIXTURES["conversations"]]
    forks = [
        (order.index(spec["forked_from"]), order.index(spec["id"]))
        for spec in FIXTURES["conversations"]
        if "forked_from" in spec
    ]
    assert forks
    assert all(source < clone for source, clone in forks)


@pytest.mark.integration
def test_clone_copies_its_source_then_diverges(seeded):
    source, clone = messages(SOURCE_CONVERSATION), messages(CLONE_CONVERSATION)
    with get_db() as session:
        source_conv, clone_conv = (
            session.get(Conversation, SOURCE_CONVERSATION),
            session.get(Conversation, CLONE_CONVERSATION),
        )
        assert clone_conv.forked_from == SOURCE_CONVERSATION
        assert clone_conv.user_id != source_conv.user_id
    assert clone[: len(source)] == source
    assert len(clone) > len(source)


@pytest.mark.integration
def test_report_message_points_to_its_report(seeded):
    with get_db() as session:
        content = session.scalar(
            select(Message.content).where(Message.conversation_id == ADMIN_CONVERSATION, Message.type == "report")
        )
        report = session.get(Report, json.loads(content)["report_id"])
        assert report.source_conversation_id == ADMIN_CONVERSATION


@pytest.mark.integration
def test_flagged_conversation_carries_the_rare_message_types(seeded):
    with get_db() as session:
        types = set(session.scalars(select(Message.type).where(Message.conversation_id == FLAGGED_CONVERSATION)))
        assert session.get(Conversation, FLAGGED_CONVERSATION).flagged_at is not None
    assert {"limit", "system"} <= types


@pytest.mark.integration
def test_conversations_have_no_session_to_resume(seeded):
    with get_db() as session:
        sessions = session.execute(
            select(Conversation.session_id, Conversation.engine_state).where(Conversation.id.in_(CONVERSATIONS))
        ).all()
    assert set(sessions) == {(None, None)}


@pytest.mark.integration
def test_dashboards_cover_each_mode(seeded):
    with get_db() as session:
        dashboards = session.scalars(select(Dashboard).where(Dashboard.slug.in_(SLUGS)))
        flags = {d.slug: (d.has_cron, d.has_api_access, d.is_archived) for d in dashboards}
    assert flags == {
        "demo-sans-cron": (False, False, False),
        "demo-cron": (True, False, False),
        "demo-publie-staging": (True, False, False),
        "demo-api-query": (False, True, False),
        "demo-archive": (True, False, True),
    }


@pytest.mark.integration
def test_only_cron_dashboards_ship_a_cron(seeded):
    uploaded = {call.args[0] for call in seeded.upload.call_args_list}
    assert {"demo-cron/cron.py", "demo-publie-staging/cron.py", "demo-archive/cron.py"} <= uploaded
    assert {"demo-sans-cron/cron.py", "demo-api-query/cron.py"}.isdisjoint(uploaded)


@pytest.mark.integration
@pytest.mark.parametrize("spec", [s for s in FIXTURES["dashboards"] if s["has_cron"]], ids=lambda s: s["slug"])
def test_cron_dashboards_get_their_own_page_and_todays_data(spec, seeded, tmp_path):
    folder = tmp_path / spec["slug"]
    page = (folder / "index.html").read_text()
    assert f"<title>{spec['title']}</title>" in page
    assert f"<th>{spec['column']}</th>" in page
    assert json.loads((folder / "data.json").read_text())["metadata"]["generated_at"] == date.today().isoformat()
    assert f"{spec['slug']}/data.json" in {call.args[0] for call in seeded.upload.call_args_list}


@pytest.mark.integration
def test_cron_dashboard_has_a_mixed_run_history(seeded):
    with get_db() as session:
        statuses = set(session.scalars(select(CronRun.status).where(CronRun.app_slug == "demo-cron")))
    assert statuses == {"success", "failure", "timeout"}


@pytest.mark.integration
def test_staging_publication_is_snapshotted_then_pushed_to_the_public_bucket(seeded):
    seeded.copy_prefix.assert_called_with(
        "interactive/demo-publie-staging/", config.S3_BUCKET, "publications/demo-publie-staging/demo01/"
    )
    seeded.sync_prefix.assert_called_with(
        "publications/demo-publie-staging/demo01/",
        config.PUBLIC_S3_BUCKET_STAGING,
        "dashboards/demo-publie-staging-demo01/",
    )
    with get_db() as session:
        publication = session.scalar(
            select(DashboardPublication).where(DashboardPublication.dashboard_slug == "demo-publie-staging")
        )
        assert (publication.environment, publication.last_refresh_status) == ("staging", "success")


@pytest.mark.integration
def test_seeding_twice_adds_nothing(seeded):
    before = counts()
    review_fixtures.seed()
    assert counts() == before


@pytest.mark.integration
def test_every_seed_restores_the_shared_copies(seeded):
    first = {call.args[0] for call in seeded.upload.call_args_list}
    seeded.upload.reset_mock()
    seeded.sync_prefix.reset_mock()
    review_fixtures.seed()
    assert {call.args[0] for call in seeded.upload.call_args_list} == first
    seeded.sync_prefix.assert_called_once()


@pytest.mark.integration
def test_next_seed_restores_the_original_state(seeded):
    before = counts()
    with get_db() as session:
        title = session.get(Conversation, FLAGGED_CONVERSATION).title
        session.execute(
            update(Conversation)
            .where(Conversation.id == FLAGGED_CONVERSATION)
            .values(title="Renommée", flagged_at=None, flag_reason=None)
        )
        session.add(
            Message(
                conversation_id=SOURCE_CONVERSATION,
                type="user",
                role="user",
                content="Et le Var ?",
                timestamp=datetime.now(timezone.utc),
            )
        )
        session.execute(delete(CronRun).where(CronRun.app_slug.in_(SLUGS)))
        session.execute(delete(DashboardPublication))
        session.execute(update(Dashboard).where(Dashboard.slug == "demo-archive").values(is_archived=False))
    review_fixtures.seed()
    with get_db() as session:
        flagged = session.get(Conversation, FLAGGED_CONVERSATION)
        assert (flagged.title, flagged.flagged_at is not None) == (title, True)
        assert session.scalar(select(Dashboard.is_archived).where(Dashboard.slug == "demo-archive"))
    assert counts() == before


@pytest.mark.integration
def test_purge_removes_the_fixtures_and_nothing_else(seeded):
    now = datetime.now(timezone.utc)
    with get_db() as session:
        session.add(Conversation(id="hors-demo", user_id="x@example.org", created_at=now, updated_at=now))
        session.add(
            Dashboard(slug="hors-demo", title="T", first_author_email="x@example.org", created_at=now, updated_at=now)
        )
        session.flush()
        session.add_all([
            Message(conversation_id="hors-demo", type="user", role="user", content="?", timestamp=now),
            Report(title="T", source_conversation_id="hors-demo", created_at=now, updated_at=now),
            CronRun(app_slug="hors-demo", started_at=now, status="success"),
            DashboardPublication(
                dashboard_slug="hors-demo",
                publication_id="abc123",
                environment="staging",
                published_by="x@example.org",
                published_at=now,
            ),
            CronRun(app_slug="demo-publie-staging-demo01", started_at=now, status="success"),
            PinnedItem(item_type="conversation", item_id=ADMIN_CONVERSATION, pinned_at=now),
            UserFavorite(
                user_id="x@example.org", item_type="dashboard", item_id="demo-cron", position=0, created_at=now
            ),
        ])
    review_fixtures.purge()
    with get_db() as session:
        left = {
            "conversations": set(session.scalars(select(Conversation.id))),
            "messages": set(session.scalars(select(Message.conversation_id))),
            "reports": set(session.scalars(select(Report.source_conversation_id))),
            "dashboards": set(session.scalars(select(Dashboard.slug))),
            "cron_runs": set(session.scalars(select(CronRun.app_slug))),
            "publications": set(session.scalars(select(DashboardPublication.dashboard_slug))),
            "pins": set(session.scalars(select(PinnedItem.item_id))),
            "favorites": set(session.scalars(select(UserFavorite.item_id))),
        }
    demo = {*CONVERSATIONS, *SLUGS, "demo-publie-staging-demo01"}
    assert [name for name, ids in left.items() if ids & demo] == []
    assert [name for name, ids in left.items() if "hors-demo" in ids] == [
        "conversations",
        "messages",
        "reports",
        "dashboards",
        "cron_runs",
        "publications",
    ]


@pytest.mark.parametrize(
    ("env", "argv", "expected"),
    [
        (Environment.REVIEW, [], "seed"),
        (Environment.REVIEW, ["--purge"], "purge"),
        (Environment.DEV, [], None),
        (Environment.STAGING, [], None),
        (Environment.PROD, ["--purge"], None),
    ],
)
def test_main_acts_only_on_review_apps(env, argv, expected, monkeypatch, mocker):
    monkeypatch.setattr(config, "ENV", env)
    actions = {name: mocker.patch.object(review_fixtures, name) for name in ("seed", "purge")}
    assert review_fixtures.main(argv) == 0
    assert [name for name, mock in actions.items() if mock.called] == ([expected] if expected else [])


def test_a_seed_failure_is_reported_without_failing_the_deploy(monkeypatch, mocker):
    monkeypatch.setattr(config, "ENV", Environment.REVIEW)
    mocker.patch.object(review_fixtures, "seed", side_effect=RuntimeError("S3 indisponible"))
    mocker.patch.object(review_fixtures, "init_sentry")
    capture = mocker.patch("sentry_sdk.capture_exception")
    assert review_fixtures.main([]) == 0
    capture.assert_called_once()


@pytest.mark.parametrize(
    ("today", "first", "last"),
    [
        (date(2026, 10, 27), "2025-11", "2026-10"),
        (date(2026, 1, 15), "2025-02", "2026-01"),
        (date(2026, 12, 31), "2026-01", "2026-12"),
    ],
)
def test_offline_cron_writes_the_twelve_months_up_to_today(today, first, last, tmp_path, monkeypatch):
    cron = load_cron()
    monkeypatch.setattr(cron.datetime, "date", type("FixedDate", (date,), {"today": classmethod(lambda cls: today)}))
    monkeypatch.chdir(tmp_path)
    cron.main()
    months = [point["mois"] for point in json.loads((tmp_path / "data.json").read_text())["series"]]
    indexes = [int(year) * 12 + int(month) for year, month in (m.split("-") for m in months)]
    assert (months[0], months[-1]) == (first, last)
    assert indexes == list(range(indexes[0], indexes[0] + 12))
