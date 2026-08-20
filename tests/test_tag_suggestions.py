"""Tests for lib/tag_suggestions — prompt, parsing strict, écriture sans application."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select

from lib.tag_suggestions import Subject, build_prompt, parse_response, run, tag_suggestions
from web.db import get_db, get_engine
from web.db import test_transaction as _test_tx
from web.models import Dashboard, DashboardTag, Tag

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]


@pytest.fixture
def db():
    with _test_tx():
        yield


@pytest.fixture(autouse=True)
def clean_suggestions():
    """Les écritures dans dashboard_storage échappent à la transaction de test — on repart à vide."""
    from lib.tag_suggestions import ensure_schema

    ensure_schema()
    with get_engine().begin() as conn:
        conn.execute(delete(tag_suggestions))
    yield


def _tag(session, name, facet, label=None, description=None):
    tag = Tag(name=name, type=facet, label=label or name, description=description, active=True)
    session.add(tag)
    session.flush()
    return tag


def _dashboard(session, slug="tdb", tags=()):
    now = datetime.now(timezone.utc)
    session.add(
        Dashboard(slug=slug, title=slug, description="desc", first_author_email="a@b.c", created_at=now, updated_at=now)
    )
    session.flush()
    for tag in tags:
        session.add(DashboardTag(dashboard_slug=slug, tag_id=tag.id))
    session.flush()


def _stored(object_id):
    with get_engine().begin() as conn:
        return conn.execute(
            select(tag_suggestions.c.current_tags, tag_suggestions.c.suggested_tags).where(
                tag_suggestions.c.object_id == object_id
            )
        ).all()


def _all_stored(object_type="dashboard"):
    with get_engine().begin() as conn:
        return conn.execute(
            select(tag_suggestions.c.object_id).where(tag_suggestions.c.object_type == object_type)
        ).all()


def _applied_tags(slug):
    with get_db() as session:
        return list(
            session.scalars(
                select(Tag.name)
                .join(DashboardTag, DashboardTag.tag_id == Tag.id)
                .where(DashboardTag.dashboard_slug == slug)
            )
        )


@pytest.mark.parametrize(
    "response,expected",
    [
        ("territoire, siae", ["territoire", "siae"]),
        ("Territoire\nSIAE", ["territoire", "siae"]),
        ("territoire, invente, siae", ["territoire", "siae"]),
        ("rien-de-valide", []),
        ("", []),
        ("territoire, territoire", ["territoire"]),
    ],
)
def test_parse_response_keeps_only_known_terms(response, expected):
    assert parse_response(response, {"territoire", "siae"}) == expected


def test_build_prompt_embeds_taxonomy_and_forbids_invention():
    prompt = build_prompt("## Usage (choisir 1 seul)\n- territoire: Périmètre", Subject("dashboard", "s", "T", "B", []))

    assert "territoire" in prompt
    assert "N'invente aucun tag" in prompt
    assert "B" in prompt


def test_run_applies_tags_and_keeps_the_audit_trail(db, mocker):
    with get_db() as session:
        existing = _tag(session, "explo", "usage")
        _tag(session, "territoire", "usage", description="Périmètre géographique")
        _dashboard(session, slug="avec-appli", tags=[existing])

    mocker.patch("web.llm.generate_text", return_value="territoire")

    result = run(object_type="dashboard", limit=10, model="test-model")

    assert result["processed"] >= 1
    assert _applied_tags("avec-appli") == ["territoire"]
    current, suggested = _stored("avec-appli")[0]
    assert current == ["explo"], "la trace garde l'état d'avant l'application"
    assert suggested == ["territoire"]


def test_run_with_apply_false_only_records(db, mocker):
    with get_db() as session:
        existing = _tag(session, "explo", "usage")
        _tag(session, "territoire", "usage")
        _dashboard(session, slug="sans-appli", tags=[existing])

    mocker.patch("web.llm.generate_text", return_value="territoire")

    run(object_type="dashboard", limit=10, model="test-model", apply=False)

    assert _applied_tags("sans-appli") == ["explo"]
    assert _stored("sans-appli")[0][1] == ["territoire"]


def test_applying_tags_does_not_bump_updated_at(db, mocker):
    from sqlalchemy import select as sa_select

    from web.models import Dashboard as DashboardModel

    with get_db() as session:
        _tag(session, "territoire", "usage")
        _dashboard(session, slug="pas-de-derive")
        before = session.scalar(sa_select(DashboardModel.updated_at).where(DashboardModel.slug == "pas-de-derive"))

    mocker.patch("web.llm.generate_text", return_value="territoire")
    run(object_type="dashboard", limit=10, model="test-model")

    with get_db() as session:
        after = session.scalar(sa_select(DashboardModel.updated_at).where(DashboardModel.slug == "pas-de-derive"))
    assert after == before, "le taguage automatique ne doit pas faire passer le TDB pour modifié"
    assert _applied_tags("pas-de-derive") == ["territoire"]


def test_run_drops_hallucinated_tags(db, mocker):
    with get_db() as session:
        _tag(session, "territoire", "usage")
        _dashboard(session, slug="halluc")

    mocker.patch("web.llm.generate_text", return_value="territoire, tag-invente")

    run(object_type="dashboard", limit=10, model="test-model")

    assert _stored("halluc")[0][1] == ["territoire"]


def test_run_counts_llm_failures_without_crashing(db, mocker):
    from web.llm_errors import LLMError

    with get_db() as session:
        _tag(session, "territoire", "usage")
        _dashboard(session, slug="ko")

    mocker.patch("web.llm.generate_text", side_effect=LLMError("boom"))

    result = run(object_type="dashboard", limit=10, model="test-model")

    assert result["failed"] >= 1
    assert result["processed"] == 0


def test_run_refuses_when_vocabulary_empty(db, mocker):
    mocker.patch("lib.tag_suggestions.load_vocabulary", return_value={})

    result = run(object_type="dashboard", limit=1)

    assert result["processed"] == 0
    assert "vocabulaire vide" in result["error"]


def test_run_rejects_unknown_object_type(db):
    with pytest.raises(ValueError, match="Type inconnu"):
        run(object_type="licorne")


def test_taxonomy_descriptions_reach_the_model(db, mocker):
    with get_db() as session:
        _tag(session, "territoire", "usage", description="Périmètre géographique")
        _dashboard(session, slug="probe")

    generate = mocker.patch("web.llm.generate_text", return_value="territoire")

    run(object_type="dashboard", limit=10, model="test-model")

    assert "Périmètre géographique" in generate.call_args[0][0]


def test_only_missing_skips_already_suggested_objects(db, mocker):
    with get_db() as session:
        _tag(session, "territoire", "usage")
        _dashboard(session, slug="deja-fait")

    generate = mocker.patch("web.llm.generate_text", return_value="territoire")
    run(object_type="dashboard", model="test-model")
    first_calls = generate.call_count

    result = run(object_type="dashboard", model="test-model")

    assert result["processed"] == 0
    assert generate.call_count == first_calls


def test_only_missing_false_reprocesses_everything(db, mocker):
    with get_db() as session:
        _tag(session, "territoire", "usage")
        _dashboard(session, slug="refait")

    mocker.patch("web.llm.generate_text", return_value="territoire")
    run(object_type="dashboard", model="test-model")

    result = run(object_type="dashboard", only_missing=False, model="test-model")

    assert result["processed"] >= 1


def test_batching_reaches_objects_beyond_the_first_page(db, mocker):
    with get_db() as session:
        _tag(session, "territoire", "usage")
        for i in range(3):
            _dashboard(session, slug=f"lot-{i}")

    mocker.patch("web.llm.generate_text", return_value="territoire")
    run(object_type="dashboard", limit=1, model="test-model")
    run(object_type="dashboard", limit=1, model="test-model")
    run(object_type="dashboard", limit=1, model="test-model")

    done = {row[0] for row in _all_stored()}
    assert {"lot-0", "lot-1", "lot-2"} <= done


def test_time_budget_stops_early_and_reports_deferred(db, mocker):
    with get_db() as session:
        _tag(session, "territoire", "usage")
        for i in range(3):
            _dashboard(session, slug=f"budget-{i}")

    mocker.patch("web.llm.generate_text", return_value="territoire")
    # Un budget nul déclenche l'arrêt dès le premier sujet.
    result = run(object_type="dashboard", model="test-model", time_budget_s=0)

    assert result["processed"] == 0
    assert result["deferred"] >= 3


def _conversation(session, conv_id, messages=("première demande",)):
    from web.models import Conversation, Message

    now = datetime.now(timezone.utc)
    session.add(Conversation(id=conv_id, user_id="a@b.c", created_at=now, updated_at=now))
    session.flush()
    for content in messages:
        session.add(Message(conversation_id=conv_id, role="user", content=content, timestamp=now))
    session.flush()


def _report(session, title="Rapport", content="corps du rapport"):
    from web.models import Report

    now = datetime.now(timezone.utc)
    report = Report(title=title, content=content, archived=0, created_at=now, updated_at=now)
    session.add(report)
    session.flush()
    return report.id


def test_conversation_subjects_uses_the_first_user_message(db):
    from lib.tag_suggestions import conversation_subjects

    with get_db() as session:
        _conversation(session, "conv-1", messages=("la première", "la seconde"))
        subjects = conversation_subjects(session)

    subject = next(s for s in subjects if s.object_id == "conv-1")
    assert "la première" in subject.body
    assert "la seconde" not in subject.body


def test_conversation_subjects_skips_conversations_without_user_message(db):
    from lib.tag_suggestions import conversation_subjects

    with get_db() as session:
        _conversation(session, "conv-muette", messages=())
        subjects = conversation_subjects(session)

    assert "conv-muette" not in [s.object_id for s in subjects]


def test_conversation_subjects_honours_exclusion(db):
    from lib.tag_suggestions import conversation_subjects

    with get_db() as session:
        _conversation(session, "conv-a")
        _conversation(session, "conv-b")
        subjects = conversation_subjects(session, exclude_ids=frozenset({"conv-a"}))

    ids = [s.object_id for s in subjects]
    assert "conv-a" not in ids and "conv-b" in ids


def test_report_subjects_excludes_by_numeric_id(db):
    from lib.tag_suggestions import report_subjects

    with get_db() as session:
        kept = _report(session, title="Gardé")
        dropped = _report(session, title="Exclu")
        subjects = report_subjects(session, exclude_ids=frozenset({str(dropped)}))

    ids = [s.object_id for s in subjects]
    assert str(kept) in ids and str(dropped) not in ids


def test_report_subjects_ignores_non_numeric_exclusions(db):
    from lib.tag_suggestions import report_subjects

    with get_db() as session:
        kept = _report(session, title="Gardé")
        subjects = report_subjects(session, exclude_ids=frozenset({"pas-un-entier"}))

    assert str(kept) in [s.object_id for s in subjects]


def test_apply_tags_on_a_conversation(db):
    from lib.tag_suggestions import apply_tags

    with get_db() as session:
        _tag(session, "territoire", "usage")
        _conversation(session, "conv-tag")

    assert apply_tags("conversation", "conv-tag", ["territoire"]) is True
    from web.database import store

    assert [t.name for t in store.get_conversation_tags("conv-tag")] == ["territoire"]


def test_apply_tags_on_a_report(db):
    from lib.tag_suggestions import apply_tags

    with get_db() as session:
        _tag(session, "territoire", "usage")
        report_id = _report(session)

    assert apply_tags("report", str(report_id), ["territoire"]) is True
    from web.database import store

    assert [t.name for t in store.get_report_tags(report_id)] == ["territoire"]


@pytest.mark.parametrize(
    "object_type,object_id",
    [
        ("dashboard", "tdb-inexistant"),
        ("licorne", "peu-importe"),
        ("report", "pas-un-entier"),
    ],
)
def test_apply_tags_returns_false_on_bad_target(db, object_type, object_id):
    from lib.tag_suggestions import apply_tags

    assert apply_tags(object_type, object_id, []) is False


def test_export_for_job_publishes_subjects_and_taxonomy(db, mocker):
    from lib.tag_suggestions import export_for_job

    with get_db() as session:
        _tag(session, "territoire", "usage", description="Périmètre géographique")
        _dashboard(session, slug="a-exporter")

    published = mocker.patch(
        "lib.job_inputs.publish_dataset",
        return_value={"url": "https://s3/x.sqlite", "row_count": 1, "format": "sqlite"},
    )

    result = export_for_job(object_types=("dashboard",))

    assert result["url"] == "https://s3/x.sqlite"
    assert "Périmètre géographique" in result["taxonomy"]
    rows = published.call_args[0][2]
    assert ["dashboard", "a-exporter"] == rows[0][:2]


def test_ingest_job_output_filters_unknown_terms(db):
    from lib.tag_suggestions import ingest_job_output

    with get_db() as session:
        _tag(session, "territoire", "usage")
        _dashboard(session, slug="ingere")

    artefact = "object_type,object_id,tags\ndashboard,ingere,territoire;invente\n"

    result = ingest_job_output(artefact)

    assert (result["ingested"], result["rejected"]) == (1, 0)
    assert _stored("ingere")[0][1] == ["territoire"]
    assert _applied_tags("ingere") == ["territoire"]


@pytest.mark.parametrize(
    "line",
    [
        "licorne,x,territoire",
        "dashboard,,territoire",
    ],
)
def test_ingest_job_output_rejects_malformed_rows(db, line):
    from lib.tag_suggestions import ingest_job_output

    with get_db() as session:
        _tag(session, "territoire", "usage")

    result = ingest_job_output(f"object_type,object_id,tags\n{line}\n")

    assert (result["ingested"], result["rejected"]) == (0, 1)


def test_suggestions_are_upserted_not_duplicated(db, mocker):
    with get_db() as session:
        _tag(session, "territoire", "usage")
        _tag(session, "explo", "usage")
        _dashboard(session, slug="upsert")

    mocker.patch("web.llm.generate_text", return_value="territoire")
    run(object_type="dashboard", limit=10, model="test-model")
    mocker.patch("web.llm.generate_text", return_value="explo")
    run(object_type="dashboard", limit=10, model="test-model", only_missing=False)

    rows = _stored("upsert")
    assert len(rows) == 1
    assert rows[0][1] == ["explo"]
