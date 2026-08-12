"""Tests for lib/tag_suggestions — prompt, parsing strict, écriture sans application."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select

from lib.tag_suggestions import Subject, build_prompt, parse_response, run, tag_suggestions
from web.db import get_db, get_engine
from web.db import test_transaction as _test_tx
from web.models import Dashboard, DashboardTag, Tag


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


def test_run_writes_suggestions_without_applying(db, mocker):
    with get_db() as session:
        existing = _tag(session, "explo", "usage")
        _tag(session, "territoire", "usage", description="Périmètre géographique")
        _dashboard(session, slug="sans-appli", tags=[existing])

    mocker.patch("web.llm.generate_text", return_value="territoire")

    result = run(object_type="dashboard", limit=10, model="test-model")

    assert result["processed"] >= 1
    current, suggested = _stored("sans-appli")[0]
    assert current == ["explo"]
    assert suggested == ["territoire"]
    assert _applied_tags("sans-appli") == ["explo"]


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
