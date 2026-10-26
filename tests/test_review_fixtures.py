"""Le jeu de démonstration des review apps : ce qu'il crée, qu'il se rejoue sans doublon, et sa purge."""

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from lib import review_fixtures
from web import config, s3
from web.db import get_db
from web.db import test_transaction as _test_tx
from web.environment import Environment
from web.models import Conversation, CronRun, Dashboard, DashboardPublication, Message, Report

ADMIN_CONVERSATION = "d3e00000-0000-4000-8000-000000000001"
GIGA_CONVERSATION = "d3e00000-0000-4000-8000-000000000002"
SOURCE_CONVERSATION = "d3e00000-0000-4000-8000-000000000003"
CLONE_CONVERSATION = "d3e00000-0000-4000-8000-000000000004"
FLAGGED_CONVERSATION = "d3e00000-0000-4000-8000-000000000005"


@pytest.fixture
def seeded(_db, tmp_path, monkeypatch, mocker):
    monkeypatch.setattr(config, "INTERACTIVE_DIR", tmp_path)
    upload = mocker.patch.object(s3.interactive, "upload", return_value=True)
    mocker.patch.object(s3, "copy_prefix", return_value=1)
    mocker.patch.object(s3, "sync_prefix", return_value=1)
    with _test_tx():
        review_fixtures.seed()
        yield upload


def contents(conversation_id):
    with get_db() as session:
        return session.scalars(
            select(Message.content).where(Message.conversation_id == conversation_id).order_by(Message.id)
        ).all()


def counts():
    with get_db() as session:
        return {
            model.__tablename__: session.scalar(select(func.count()).select_from(model))
            for model in (Conversation, Message, Report, Dashboard, CronRun, DashboardPublication)
        }


@pytest.mark.integration
def test_giga_conversation_holds_thousands_of_messages(seeded):
    assert len(contents(GIGA_CONVERSATION)) >= 6000


@pytest.mark.integration
def test_admin_conversation_belongs_to_the_first_admin(seeded):
    with get_db() as session:
        assert session.get(Conversation, ADMIN_CONVERSATION).user_id == config.ADMIN_USERS[0]


@pytest.mark.integration
def test_clone_copies_its_source_then_diverges(seeded):
    source, clone = contents(SOURCE_CONVERSATION), contents(CLONE_CONVERSATION)
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
        sessions = session.execute(select(Conversation.session_id, Conversation.engine_state)).all()
    assert set(sessions) == {(None, None)}


@pytest.mark.integration
def test_dashboards_cover_each_mode(seeded):
    with get_db() as session:
        flags = {d.slug: (d.has_cron, d.has_api_access, d.is_archived) for d in session.scalars(select(Dashboard))}
    assert flags == {
        "demo-sans-cron": (False, False, False),
        "demo-cron": (True, False, False),
        "demo-publie-staging": (True, False, False),
        "demo-api-query": (False, True, False),
        "demo-archive": (True, False, True),
    }


@pytest.mark.integration
def test_only_cron_dashboards_ship_a_cron(seeded):
    uploaded = {call.args[0] for call in seeded.call_args_list}
    assert {"demo-cron/cron.py", "demo-publie-staging/cron.py", "demo-archive/cron.py"} <= uploaded
    assert {"demo-sans-cron/cron.py", "demo-api-query/cron.py"}.isdisjoint(uploaded)


@pytest.mark.integration
def test_cron_dashboard_has_a_mixed_run_history(seeded):
    with get_db() as session:
        statuses = set(session.scalars(select(CronRun.status).where(CronRun.app_slug == "demo-cron")))
    assert statuses == {"success", "failure", "timeout"}


@pytest.mark.integration
def test_staging_publication_is_pushed_to_the_public_bucket(seeded):
    with get_db() as session:
        publication = session.scalar(select(DashboardPublication))
        assert (publication.dashboard_slug, publication.environment) == ("demo-publie-staging", "staging")
        assert publication.last_refresh_status == "success"


@pytest.mark.integration
def test_seeding_twice_adds_nothing(seeded):
    before = counts()
    review_fixtures.seed()
    assert counts() == before


@pytest.mark.integration
def test_purge_removes_the_fixtures_and_nothing_else(seeded):
    now = datetime.now(timezone.utc)
    with get_db() as session:
        session.add(Conversation(id="hors-demo", user_id="x@example.org", created_at=now, updated_at=now))
        session.add(
            Dashboard(slug="hors-demo", title="T", first_author_email="x@example.org", created_at=now, updated_at=now)
        )
    review_fixtures.purge()
    with get_db() as session:
        assert session.scalars(select(Conversation.id)).all() == ["hors-demo"]
        assert session.scalars(select(Dashboard.slug)).all() == ["hors-demo"]
    remaining = counts()
    assert (remaining["messages"], remaining["reports"], remaining["cron_runs"]) == (0, 0, 0)


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
