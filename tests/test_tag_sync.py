"""Tests for lib/tag_sync — parsing, garde-fous, renommage par page_id, désactivation."""

import pytest
from sqlalchemy import select

from lib.tag_sync import fetch_terms, parse_row, sync_state, sync_tags
from lib.taxonomy import load_implications
from web.db import get_db
from web.db import test_transaction as _test_tx
from web.models import Dashboard, DashboardTag, Tag

# Why: `query_database` est mocké — seul le parsing d'id est traversé, aucun accès réseau.
FAKE_TAGS_DB = "0" * 32


@pytest.fixture
def db():
    with _test_tx():
        yield


@pytest.fixture
def notion_configured(mocker):
    mocker.patch("web.config.NOTION_TAGS_DB", FAKE_TAGS_DB)
    mocker.patch("web.config.NOTION_TOKEN", "secret")


def _page(page_id, slug, facet="theme", label=None, description=None, active=True, implies=()):
    return {
        "id": page_id,
        "properties": {
            "Slug": {"type": "title", "title": [{"plain_text": slug}]},
            "Libellé": {"type": "rich_text", "rich_text": [{"plain_text": label}] if label else []},
            "Description": {"type": "rich_text", "rich_text": [{"plain_text": description}] if description else []},
            "Facette": {"type": "select", "select": {"name": facet} if facet else None},
            "Actif": {"type": "checkbox", "checkbox": active},
            "Implique": {"type": "relation", "relation": [{"id": i} for i in implies]},
        },
    }


def _mock_pages(mocker, pages):
    return mocker.patch("lib.notion.query_database", return_value=pages)


def _dashboard(session, slug="tdb"):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    session.add(Dashboard(slug=slug, title="T", first_author_email="a@b.c", created_at=now, updated_at=now))
    session.flush()


def test_parse_row_normalizes_slug_and_defaults_label():
    term, reason = parse_row(_page("p1", "Réseau d'intervenants", facet="feature"))

    assert reason is None
    assert term.name == "reseau-d-intervenants"
    assert term.label == "reseau-d-intervenants"


@pytest.mark.parametrize(
    "slug,facet,fragment",
    [
        ("", "theme", "slug vide"),
        ("   ", "theme", "slug vide"),
        ("!!!", "theme", "après normalisation"),
        ("valide", "inconnue", "facette inconnue"),
        ("valide", None, "facette inconnue"),
    ],
)
def test_parse_row_rejects_invalid(slug, facet, fragment):
    term, reason = parse_row(_page("p1", slug, facet=facet))

    assert term is None
    assert fragment in reason


def test_fetch_terms_rejects_duplicate_slugs(mocker, notion_configured):
    _mock_pages(mocker, [_page("p1", "qualite"), _page("p2", "Qualité")])

    terms, rejected = fetch_terms()

    assert [t.name for t in terms] == ["qualite"]
    assert any("doublon" in r for r in rejected)


def test_sync_creates_terms(db, mocker, notion_configured):
    _mock_pages(mocker, [_page("p1", "usagers", "theme", label="Usagers", description="Personnes accompagnées")])

    result = sync_tags()

    assert result.created == 1
    with get_db() as session:
        tag = session.scalar(select(Tag).where(Tag.name == "usagers"))
        assert (tag.type, tag.label, tag.description, tag.active) == (
            "theme",
            "Usagers",
            "Personnes accompagnées",
            True,
        )


def test_rename_keyed_on_page_id_preserves_assignments(db, mocker, notion_configured):
    _mock_pages(mocker, [_page("p1", "candidats", "theme", label="Candidats")])
    sync_tags()

    with get_db() as session:
        _dashboard(session)
        tag = session.scalar(select(Tag).where(Tag.name == "candidats"))
        session.add(DashboardTag(dashboard_slug="tdb", tag_id=tag.id))
        session.flush()
        tag_id = tag.id

    _mock_pages(mocker, [_page("p1", "usagers", "theme", label="Usagers")])
    result = sync_tags()

    assert result.updated == 1
    with get_db() as session:
        assert session.get(Tag, tag_id).name == "usagers"
        assert session.scalar(select(DashboardTag.tag_id).where(DashboardTag.dashboard_slug == "tdb")) == tag_id


def test_missing_row_with_assignments_is_deactivated_not_deleted(db, mocker, notion_configured):
    _mock_pages(mocker, [_page(f"p{i}", f"terme-{i}") for i in range(5)])
    sync_tags()

    with get_db() as session:
        _dashboard(session)
        tag = session.scalar(select(Tag).where(Tag.name == "terme-0"))
        session.add(DashboardTag(dashboard_slug="tdb", tag_id=tag.id))
        session.flush()

    _mock_pages(mocker, [_page(f"p{i}", f"terme-{i}") for i in range(1, 5)])
    result = sync_tags()

    assert (result.deactivated, result.deleted) == (1, 0)
    with get_db() as session:
        assert session.scalar(select(Tag).where(Tag.name == "terme-0")).active is False


def test_missing_row_without_assignments_is_deleted(db, mocker, notion_configured):
    _mock_pages(mocker, [_page(f"p{i}", f"terme-{i}") for i in range(5)])
    sync_tags()

    _mock_pages(mocker, [_page(f"p{i}", f"terme-{i}") for i in range(1, 5)])
    result = sync_tags()

    assert (result.deactivated, result.deleted) == (0, 1)
    with get_db() as session:
        assert session.scalar(select(Tag).where(Tag.name == "terme-0")) is None


def test_empty_fetch_is_refused_and_changes_nothing(db, mocker, notion_configured):
    _mock_pages(mocker, [_page("p1", "usagers")])
    sync_tags()

    _mock_pages(mocker, [])
    result = sync_tags()

    assert not result.applied
    assert "vide" in result.error
    with get_db() as session:
        assert session.scalar(select(Tag).where(Tag.name == "usagers")) is not None


def test_shrunk_fetch_is_refused(db, mocker, notion_configured):
    _mock_pages(mocker, [_page(f"p{i}", f"terme-{i}") for i in range(10)])
    sync_tags()

    _mock_pages(mocker, [_page("p0", "terme-0")])
    result = sync_tags()

    assert not result.applied
    assert "suspect" in result.error
    with get_db() as session:
        assert session.scalar(select(Tag).where(Tag.name == "terme-9")) is not None


def test_implications_are_applied(db, mocker, notion_configured):
    _mock_pages(
        mocker,
        [
            _page("p1", "siae", "audience", implies=("p2",)),
            _page("p2", "solutions-structurees", "audience"),
        ],
    )

    result = sync_tags()

    assert result.implications == 1
    with get_db() as session:
        assert load_implications(session) == {"siae": {"solutions-structurees"}}


def test_dry_run_reports_without_writing(db, mocker, notion_configured):
    _mock_pages(mocker, [_page("p1", "usagers")])

    result = sync_tags(dry_run=True)

    assert result.created == 1
    assert not result.applied
    with get_db() as session:
        assert session.scalar(select(Tag).where(Tag.name == "usagers")) is None


def test_dry_run_preserves_rows_written_before_it(db, mocker, notion_configured):
    with get_db() as session:
        session.add(Tag(name="ecrit-avant", type="theme", label="Avant", active=True))
        session.flush()

    _mock_pages(mocker, [_page("p1", "usagers")])
    sync_tags(dry_run=True)

    with get_db() as session:
        assert session.scalar(select(Tag).where(Tag.name == "ecrit-avant")) is not None


def test_dry_run_records_no_sync_state_when_refused(db, mocker, notion_configured):
    _mock_pages(mocker, [_page("p1", "usagers")])
    sync_tags()

    _mock_pages(mocker, [])
    before = sync_state()
    sync_tags(dry_run=True)

    assert sync_state()["last_synced_at"] == before["last_synced_at"]


def test_dry_run_reports_implication_count(db, mocker, notion_configured):
    _mock_pages(
        mocker,
        [_page("p1", "siae", "audience", implies=("p2",)), _page("p2", "solutions-structurees", "audience")],
    )

    assert sync_tags(dry_run=True).implications == 1


def test_name_fallback_never_steals_another_pages_row(db, mocker, notion_configured):
    _mock_pages(mocker, [_page("p1", "partage", "theme"), _page("p2", "autre", "theme")])
    sync_tags()

    with get_db() as session:
        owned_id = session.scalar(select(Tag.id).where(Tag.name == "partage"))

    # p3 réclame un slug déjà détenu par p1 : il doit créer sa propre ligne, pas adopter celle de p1.
    _mock_pages(
        mocker,
        [_page("p1", "partage", "theme"), _page("p2", "autre", "theme"), _page("p3", "encore", "theme")],
    )
    sync_tags()

    with get_db() as session:
        assert session.get(Tag, owned_id).notion_page_id == "p1"


def test_pending_terms_lists_proposals_with_usage_counts(db):
    from datetime import datetime, timezone

    from lib.tag_sync import pending_terms
    from web.models import Dashboard, DashboardTag

    with get_db() as session:
        proposed = Tag(name="regies", type="audience", label="Régies", active=True, pending=True)
        session.add(proposed)
        session.add(Tag(name="promu", type="audience", label="Promu", active=True, pending=False))
        now = datetime.now(timezone.utc)
        session.add(Dashboard(slug="tdb", title="T", first_author_email="a@b.c", created_at=now, updated_at=now))
        session.flush()
        session.add(DashboardTag(dashboard_slug="tdb", tag_id=proposed.id))
        session.flush()

    assert pending_terms() == [{"name": "regies", "facet": "audience", "label": "Régies", "usages": 1}]


def test_pending_terms_ignores_deactivated_proposals(db):
    from lib.tag_sync import pending_terms

    with get_db() as session:
        session.add(Tag(name="rejete", type="audience", label="Rejeté", active=False, pending=True))
        session.flush()

    assert pending_terms() == []


def test_purge_legacy_tags_reports_before_deleting(db, mocker, notion_configured):
    from lib.tag_sync import purge_legacy_tags

    _mock_pages(mocker, [_page("p1", "synchro", "theme")])
    sync_tags()
    with get_db() as session:
        session.add(Tag(name="herite", type="theme", label="Hérité", active=False))
        session.flush()

    report = purge_legacy_tags(dry_run=True)

    assert report["names"] == ["herite"]
    with get_db() as session:
        assert session.scalar(select(Tag).where(Tag.name == "herite")) is not None


def test_purge_legacy_tags_spares_pending_proposals(db, mocker, notion_configured):
    from lib.tag_sync import purge_legacy_tags

    _mock_pages(mocker, [_page("p1", "synchro", "theme")])
    sync_tags()
    with get_db() as session:
        session.add(Tag(name="herite", type="theme", label="Hérité", active=False))
        session.add(Tag(name="propose", type="audience", label="Proposé", active=True, pending=True))
        session.flush()

    report = purge_legacy_tags(dry_run=False)

    assert report["names"] == ["herite"]
    with get_db() as session:
        assert session.scalar(select(Tag).where(Tag.name == "propose")) is not None


def test_purge_legacy_tags_spares_notion_managed_terms(db, mocker, notion_configured):
    from lib.tag_sync import purge_legacy_tags

    _mock_pages(mocker, [_page("p1", "synchro", "theme")])
    sync_tags()
    with get_db() as session:
        session.add(Tag(name="herite", type="theme", label="Hérité", active=False))
        session.flush()

    purge_legacy_tags(dry_run=False)

    with get_db() as session:
        assert session.scalar(select(Tag).where(Tag.name == "herite")) is None
        assert session.scalar(select(Tag).where(Tag.name == "synchro")) is not None


def test_sync_without_config_returns_error(db, mocker):
    mocker.patch("web.config.NOTION_TAGS_DB", None)

    result = sync_tags()

    assert not result.applied
    assert "NOTION_TAGS_DB" in result.error
