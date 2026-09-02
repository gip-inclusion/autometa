"""Tests for the /dashboards facet filters — comptage, expansion des implications, ordre."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from web.database import store
from web.db import get_db
from web.db import test_transaction as _test_tx
from web.models import Dashboard, DashboardTag, Tag, TagImplication
from web.routes.dashboards import FACET_TERM_CAP, facet_filters

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]


@pytest.fixture
def db():
    with _test_tx():
        yield


def _tag(session, name, facet, label=None):
    tag = Tag(name=name, type=facet, label=label or name, active=True)
    session.add(tag)
    session.flush()
    return tag


def _dashboard(session, slug, tags=(), archived=False):
    now = datetime.now(timezone.utc)
    session.add(
        Dashboard(
            slug=slug, title=slug, first_author_email="a@b.c", created_at=now, updated_at=now, is_archived=archived
        )
    )
    session.flush()
    for tag in tags:
        session.add(DashboardTag(dashboard_slug=slug, tag_id=tag.id))
    session.flush()


def test_used_tags_are_grouped_by_facet_with_counts(db):
    with get_db() as session:
        territoire = _tag(session, "territoire", "usage", "Territoire")
        siae = _tag(session, "siae", "audience", "SIAE")
        _tag(session, "jamais-utilise", "theme")
        _dashboard(session, "a", [territoire, siae])
        _dashboard(session, "b", [territoire])

    used = store.get_used_dashboard_tags_by_type()

    assert used["usage"] == [{"name": "territoire", "label": "Territoire", "count": 2}]
    assert used["audience"] == [{"name": "siae", "label": "SIAE", "count": 1}]
    assert "theme" not in used


def test_used_tags_exclude_archived_dashboards(db):
    with get_db() as session:
        territoire = _tag(session, "territoire", "usage")
        _dashboard(session, "vivant", [territoire])
        _dashboard(session, "mort", [territoire], archived=True)

    assert store.get_used_dashboard_tags_by_type()["usage"][0]["count"] == 1


def test_used_tags_can_be_restricted_to_some_dashboards(db):
    with get_db() as session:
        territoire = _tag(session, "territoire", "usage")
        siae = _tag(session, "siae", "audience")
        _dashboard(session, "publie", [territoire])
        _dashboard(session, "brouillon", [territoire, siae])

    used = store.get_used_dashboard_tags_by_type(slugs={"publie"})

    assert used["usage"][0]["count"] == 1
    assert "audience" not in used


def test_filter_by_tag_returns_only_matching(db):
    with get_db() as session:
        territoire = _tag(session, "territoire", "usage")
        _dashboard(session, "avec", [territoire])
        _dashboard(session, "sans")

    assert [d["slug"] for d in store.list_dashboards(tag_names=["territoire"])] == ["avec"]


def test_filters_combine_with_and(db):
    with get_db() as session:
        territoire = _tag(session, "territoire", "usage")
        siae = _tag(session, "siae", "audience")
        _dashboard(session, "les-deux", [territoire, siae])
        _dashboard(session, "un-seul", [territoire])

    assert [d["slug"] for d in store.list_dashboards(tag_names=["territoire", "siae"])] == ["les-deux"]


def test_filtering_on_generic_term_matches_implied_specific(db):
    with get_db() as session:
        solutions = _tag(session, "solutions-structurees", "audience")
        siae = _tag(session, "siae", "audience")
        session.add(TagImplication(tag_id=siae.id, implies_tag_id=solutions.id))
        session.flush()
        _dashboard(session, "tague-siae", [siae])
        _dashboard(session, "hors-sujet")

    assert [d["slug"] for d in store.list_dashboards(tag_names=["solutions-structurees"])] == ["tague-siae"]


def test_filtering_on_specific_term_does_not_match_generic(db):
    with get_db() as session:
        solutions = _tag(session, "solutions-structurees", "audience")
        siae = _tag(session, "siae", "audience")
        session.add(TagImplication(tag_id=siae.id, implies_tag_id=solutions.id))
        session.flush()
        _dashboard(session, "tague-generique", [solutions])

    assert store.list_dashboards(tag_names=["siae"]) == []


def test_filtering_expands_implications_transitively(db):
    with get_db() as session:
        large = _tag(session, "niveau-large", "theme")
        moyen = _tag(session, "niveau-moyen", "audience")
        precis = _tag(session, "niveau-precis", "audience")
        session.add(TagImplication(tag_id=precis.id, implies_tag_id=moyen.id))
        session.add(TagImplication(tag_id=moyen.id, implies_tag_id=large.id))
        session.flush()
        _dashboard(session, "tague-precis", [precis])

    assert [d["slug"] for d in store.list_dashboards(tag_names=["niveau-large"])] == ["tague-precis"]


def test_archived_view_honours_tag_filters(db):
    with get_db() as session:
        territoire = _tag(session, "territoire", "usage")
        _dashboard(session, "archive-tague", [territoire], archived=True)
        _dashboard(session, "archive-nu", archived=True)

    assert [d["slug"] for d in store.list_archived_dashboards(tag_names=["territoire"])] == ["archive-tague"]


def test_facet_filters_order_puts_usage_first(db):
    with get_db() as session:
        _dashboard(session, "a", [_tag(session, "siae", "audience"), _tag(session, "territoire", "usage")])

    assert [f["name"] for f in facet_filters([])][:2] == ["usage", "audience"]


def test_facet_filters_hide_facets_without_used_terms(db):
    with get_db() as session:
        _dashboard(session, "a", [_tag(session, "territoire", "usage")])
        _tag(session, "mesure-non-utilisee", "mesure")

    assert [f["name"] for f in facet_filters([])] == ["usage"]


def test_term_order_does_not_change_when_a_term_is_selected(db):
    with get_db() as session:
        for i, count in enumerate((5, 3, 1)):
            tag = _tag(session, f"terme-{i}", "usage", f"Terme {i}")
            for n in range(count):
                _dashboard(session, f"d{i}-{n}", [tag])

    before = [t["name"] for t in facet_filters([])[0]["terms"]]
    after = [t["name"] for t in facet_filters(["terme-2"])[0]["terms"]]

    assert before == after, "cocher une case ne doit pas réordonner la liste"


def test_selected_term_stays_visible_despite_cap(db):
    with get_db() as session:
        rare = _tag(session, "rare", "usage", "Rare")
        _dashboard(session, "rare-only", [rare])
        for i in range(FACET_TERM_CAP + 2):
            common = _tag(session, f"commun-{i}", "usage", f"Commun {i}")
            for n in range(3):
                _dashboard(session, f"d{i}-{n}", [common])

    usage = next(f for f in facet_filters(["rare"]) if f["name"] == "usage")

    assert "rare" in [t["name"] for t in usage["terms"]]
    assert usage["overflow"]


def test_unselected_rare_term_falls_into_overflow(db):
    with get_db() as session:
        rare = _tag(session, "rare", "usage", "Rare")
        _dashboard(session, "rare-only", [rare])
        for i in range(FACET_TERM_CAP + 2):
            common = _tag(session, f"commun-{i}", "usage", f"Commun {i}")
            for n in range(3):
                _dashboard(session, f"d{i}-{n}", [common])

    usage = next(f for f in facet_filters([]) if f["name"] == "usage")

    assert "rare" in [t["name"] for t in usage["overflow"]]


def test_inactive_tags_are_not_offered_as_filters(db):
    with get_db() as session:
        retire = _tag(session, "retire", "usage")
        _dashboard(session, "a", [retire])
        session.scalar(select(Tag).where(Tag.name == "retire")).active = False
        session.flush()

    assert facet_filters([]) == []
