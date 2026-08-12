"""Tests for tag editing on /dashboards/{slug}/edit — cardinalité, endpoint, rendu."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from lib.taxonomy import apply_toggle
from web.db import get_db
from web.db import test_transaction as _test_tx
from web.models import Dashboard, DashboardTag, Tag

HEADERS = {"X-Forwarded-Email": "test@example.com"}


@pytest.fixture
def db():
    with _test_tx():
        yield


def _tag(session, name, facet, label=None):
    tag = Tag(name=name, type=facet, label=label or name, active=True)
    session.add(tag)
    session.flush()
    return tag


def _dashboard(session, slug="tdb", tags=()):
    now = datetime.now(timezone.utc)
    session.add(Dashboard(slug=slug, title=slug, first_author_email="a@b.c", created_at=now, updated_at=now))
    session.flush()
    for tag in tags:
        session.add(DashboardTag(dashboard_slug=slug, tag_id=tag.id))
    session.flush()


def _tags_of(slug="tdb"):
    with get_db() as session:
        return set(
            session.scalars(
                select(Tag.name)
                .join(DashboardTag, DashboardTag.tag_id == Tag.id)
                .where(DashboardTag.dashboard_slug == slug)
            )
        )


FACET_OF = {"territoire": "usage", "explo": "usage", "siae": "audience", "ccas": "audience"}


@pytest.mark.parametrize(
    "current,toggled,expected",
    [
        ([], "siae", ["siae"]),
        (["siae"], "siae", []),
        (["siae"], "ccas", ["siae", "ccas"]),
        (["territoire"], "explo", ["explo"]),
        (["territoire", "siae"], "explo", ["siae", "explo"]),
        (["territoire"], "territoire", []),
    ],
)
def test_apply_toggle(current, toggled, expected):
    assert apply_toggle(current, toggled, FACET_OF) == expected


def test_toggle_endpoint_adds_tag(db, app, client):
    with get_db() as session:
        _tag(session, "siae", "audience")
        _dashboard(session)

    resp = client.post("/api/dashboards/tdb/tags", data={"tag": "siae"}, headers=HEADERS)

    assert resp.status_code == 200
    assert _tags_of() == {"siae"}


def test_toggle_endpoint_removes_existing_tag(db, app, client):
    with get_db() as session:
        siae = _tag(session, "siae", "audience")
        _dashboard(session, tags=[siae])

    client.post("/api/dashboards/tdb/tags", data={"tag": "siae"}, headers=HEADERS)

    assert _tags_of() == set()


def test_single_cardinality_facet_replaces(db, app, client):
    with get_db() as session:
        territoire = _tag(session, "territoire", "usage")
        _tag(session, "explo", "usage")
        _dashboard(session, tags=[territoire])

    client.post("/api/dashboards/tdb/tags", data={"tag": "explo"}, headers=HEADERS)

    assert _tags_of() == {"explo"}


def test_toggle_rejects_unknown_tag(db, app, client):
    with get_db() as session:
        _dashboard(session)

    resp = client.post("/api/dashboards/tdb/tags", data={"tag": "inconnu"}, headers=HEADERS)

    assert resp.status_code == 400
    assert _tags_of() == set()


def test_toggle_rejects_inactive_tag(db, app, client):
    with get_db() as session:
        tag = _tag(session, "retire", "audience")
        tag.active = False
        session.flush()
        _dashboard(session)

    resp = client.post("/api/dashboards/tdb/tags", data={"tag": "retire"}, headers=HEADERS)

    assert resp.status_code == 400


def test_toggle_returns_404_for_unknown_dashboard(db, app, client):
    with get_db() as session:
        _tag(session, "siae", "audience")

    resp = client.post("/api/dashboards/absent/tags", data={"tag": "siae"}, headers=HEADERS)

    assert resp.status_code == 404


def test_toggle_response_returns_oob_summary(db, app, client):
    with get_db() as session:
        _tag(session, "siae", "audience", label="SIAE")
        _dashboard(session)

    resp = client.post("/api/dashboards/tdb/tags", data={"tag": "siae"}, headers=HEADERS)

    assert 'id="tagsum-audience"' in resp.text
    assert 'hx-swap-oob="true"' in resp.text
    assert "SIAE" in resp.text


def test_clearing_a_single_value_facet(db, app, client):
    with get_db() as session:
        territoire = _tag(session, "territoire", "usage")
        _dashboard(session, tags=[territoire])

    resp = client.post("/api/dashboards/tdb/tags", data={"tag": "", "facet": "usage"}, headers=HEADERS)

    assert resp.status_code == 200
    assert _tags_of() == set()


def test_clearing_a_facet_leaves_other_facets_intact(db, app, client):
    with get_db() as session:
        territoire = _tag(session, "territoire", "usage")
        siae = _tag(session, "siae", "audience")
        _dashboard(session, tags=[territoire, siae])

    client.post("/api/dashboards/tdb/tags", data={"tag": "", "facet": "usage"}, headers=HEADERS)

    assert _tags_of() == {"siae"}


def test_summary_shows_first_label_and_a_count_badge_when_multiple(db, app, client):
    with get_db() as session:
        acheteurs = _tag(session, "acheteurs", "theme", label="Acheteurs")
        commandes = _tag(session, "commandes", "theme", label="Commandes")
        _dashboard(session, tags=[acheteurs, commandes])

    resp = client.get("/dashboards/tdb/edit", headers=HEADERS)

    assert '<span class="dashboard-tags-badge">2</span>' in resp.text
    assert "Acheteurs" in resp.text
    assert "Acheteurs, Commandes" in resp.text


def test_summary_omits_badge_for_a_single_selection(db, app, client):
    with get_db() as session:
        acheteurs = _tag(session, "acheteurs", "theme", label="Acheteurs")
        _dashboard(session, tags=[acheteurs])

    resp = client.get("/dashboards/tdb/edit", headers=HEADERS)

    assert "dashboard-tags-badge" not in resp.text


def test_create_tag_proposes_it_as_pending_and_applies_it(db, app, client):
    with get_db() as session:
        _dashboard(session)

    resp = client.post(
        "/api/dashboards/tdb/tags/new", data={"facet": "audience", "label": "Régies de quartier"}, headers=HEADERS
    )

    assert resp.status_code == 200
    assert _tags_of() == {"regies-de-quartier"}
    with get_db() as session:
        created = session.scalar(select(Tag).where(Tag.name == "regies-de-quartier"))
        assert (created.type, created.pending, created.active) == ("audience", True, True)


@pytest.mark.parametrize("facet", ["usage", "mesure", "source"])
def test_create_tag_refused_on_closed_facets(db, app, client, facet):
    with get_db() as session:
        _dashboard(session)

    resp = client.post("/api/dashboards/tdb/tags/new", data={"facet": facet, "label": "Inventé"}, headers=HEADERS)

    assert resp.status_code == 400
    assert _tags_of() == set()


def test_create_tag_reuses_an_existing_term_instead_of_duplicating(db, app, client):
    with get_db() as session:
        _tag(session, "siae", "audience", label="SIAE")
        _dashboard(session)

    client.post("/api/dashboards/tdb/tags/new", data={"facet": "audience", "label": "SIAE"}, headers=HEADERS)

    assert _tags_of() == {"siae"}
    with get_db() as session:
        assert session.scalar(select(Tag).where(Tag.name == "siae")).pending is False


def test_extensible_facet_offers_a_single_search_and_create_field(db, app, client):
    with get_db() as session:
        _tag(session, "siae", "audience", label="SIAE")
        _dashboard(session)

    html = client.get("/dashboards/tdb/edit", headers=HEADERS).text

    assert html.count('name="label"') == 3  # une seule zone de saisie par facette extensible
    assert "Filtrer ou créer" in html
    assert "dashboard-tags-create" in html


def test_create_button_includes_an_element_that_actually_exists(db, app, client):
    """Why: htmx ne chaîne pas les sélecteurs étendus — un hx-include invalide poste sans libellé."""
    import re

    with get_db() as session:
        _dashboard(session)

    html = client.get("/dashboards/tdb/edit", headers=HEADERS).text
    targets = re.findall(r'hx-include="([^"]+)"', html)

    assert targets
    for target in targets:
        assert target.startswith("#"), f"sélecteur htmx non résolu de façon fiable : {target}"
        assert f'id="{target[1:]}"' in html


def test_create_tag_rejects_empty_label(db, app, client):
    with get_db() as session:
        _dashboard(session)

    resp = client.post("/api/dashboards/tdb/tags/new", data={"facet": "theme", "label": "  !! "}, headers=HEADERS)

    assert resp.status_code == 400


def test_pending_terms_are_excluded_from_the_tagger_vocabulary(db):
    from lib.taxonomy import load_vocabulary

    with get_db() as session:
        _tag(session, "valide", "theme")
        propose = _tag(session, "propose", "theme")
        propose.pending = True
        session.flush()

        offered = load_vocabulary(session, include_pending=False)
        shown = load_vocabulary(session)

    assert "propose" not in [t.name for t in offered["theme"]]
    assert "propose" in [t.name for t in shown["theme"]]


def test_sync_promotion_clears_pending(db, mocker):
    from lib.tag_sync import sync_tags

    mocker.patch("web.config.NOTION_TAGS_DB", "0" * 32)
    mocker.patch("web.config.NOTION_TOKEN", "secret")
    with get_db() as session:
        proposed = _tag(session, "regies-de-quartier", "audience", label="Régies de quartier")
        proposed.pending = True
        session.flush()

    mocker.patch(
        "lib.notion.query_database",
        return_value=[
            {
                "id": "p1",
                "properties": {
                    "Slug": {"type": "title", "title": [{"plain_text": "regies-de-quartier"}]},
                    "Libellé": {"type": "rich_text", "rich_text": [{"plain_text": "Régies de quartier"}]},
                    "Description": {"type": "rich_text", "rich_text": []},
                    "Facette": {"type": "select", "select": {"name": "audience"}},
                    "Actif": {"type": "checkbox", "checkbox": True},
                    "Implique": {"type": "relation", "relation": []},
                },
            }
        ],
    )
    sync_tags()

    with get_db() as session:
        assert session.scalar(select(Tag).where(Tag.name == "regies-de-quartier")).pending is False


def test_edit_page_renders_facets_with_terms_and_every_extensible_one(db, app, client):
    with get_db() as session:
        siae = _tag(session, "siae", "audience", label="SIAE")
        _tag(session, "territoire", "usage", label="Territoire")
        _dashboard(session, tags=[siae])

    resp = client.get("/dashboards/tdb/edit", headers=HEADERS)

    # usage/audience portent des termes ; feature/theme sont extensibles donc offertes même vides.
    for facet in ("usage", "audience", "feature", "theme"):
        assert f'id="tagsum-{facet}"' in resp.text
    # mesure et source sont vides et non extensibles.
    for facet in ("mesure", "source"):
        assert f'id="tagsum-{facet}"' not in resp.text


def test_edit_page_renders_tag_editor(db, app, client):
    with get_db() as session:
        siae = _tag(session, "siae", "audience", label="SIAE")
        _dashboard(session, tags=[siae])

    resp = client.get("/dashboards/tdb/edit", headers=HEADERS)

    assert resp.status_code == 200
    assert "dashboardTags" in resp.text
