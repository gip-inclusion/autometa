"""Tests for lib/taxonomy (facettes, normalisation, implications, prompt)."""

import pytest

from lib.taxonomy import (
    FACETS,
    Term,
    build_prompt_taxonomy,
    expand_implications,
    load_implications,
    load_vocabulary,
    normalize_tag_name,
    normalize_tags,
    ordered_facets,
)
from web.db import get_db
from web.db import test_transaction as _test_tx
from web.models import Tag, TagImplication


@pytest.fixture
def db():
    with _test_tx():
        yield


def _tag(session, name, facet="theme", label=None, active=True, description=None):
    tag = Tag(name=name, type=facet, label=label or name, active=active, description=description)
    session.add(tag)
    session.flush()
    return tag


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Réseau d'intervenants", "reseau-d-intervenants"),
        ("  ACTES métiers  ", "actes-metiers"),
        ("Qualité", "qualite"),
        ("Passation + délégation", "passation-delegation"),
        ("mise en avant de l'offre", "mise-en-avant-de-l-offre"),
        ("déjà-kebab", "deja-kebab"),
        ("", None),
        ("   ", None),
        ("---", None),
        ("!!!", None),
    ],
)
def test_normalize_tag_name(raw, expected):
    assert normalize_tag_name(raw) == expected


def test_normalize_tags_dedupes_preserving_order():
    assert normalize_tags(["Qualité", "qualite", "Impact", "  "]) == ["qualite", "impact"]


def test_ordered_facets_puts_usage_first_for_dashboards():
    assert ordered_facets("dashboard")[0].name == "usage"


def test_ordered_facets_puts_feature_first_for_conversations():
    assert ordered_facets("conversation")[0].name == "feature"


def test_ordered_facets_falls_back_to_declaration_order():
    assert [f.name for f in ordered_facets("inconnu")] == [f.name for f in FACETS]


def test_expand_implications_is_transitive():
    implications = {"siae": {"solutions-structurees"}, "solutions-structurees": {"structures"}}
    assert expand_implications(["siae"], implications) == {"siae", "solutions-structurees", "structures"}


def test_expand_implications_survives_cycles():
    implications = {"a": {"b"}, "b": {"a"}}
    assert expand_implications(["a"], implications) == {"a", "b"}


def test_expand_implications_without_match_returns_input():
    assert expand_implications(["orphelin"], {}) == {"orphelin"}


def test_build_prompt_taxonomy_states_cardinality_and_uses_description():
    vocabulary = {
        "usage": [Term("territoire", "Territoire", "usage", "Périmètre géographique")],
        "theme": [Term("usagers", "Usagers", "theme", None)],
    }
    rendered = build_prompt_taxonomy(vocabulary)

    assert "choisir 1 seul" in rendered
    assert "0 à 2" in rendered
    assert "- territoire: Périmètre géographique" in rendered
    assert "- usagers: Usagers" in rendered


def test_build_prompt_taxonomy_skips_empty_facets():
    assert "Fonctionnalité" not in build_prompt_taxonomy({"usage": [Term("meta", "Méta", "usage")]})


def test_load_vocabulary_groups_by_facet_and_hides_inactive(db):
    with get_db() as session:
        _tag(session, "t-usagers", "facet-a", label="Usagers")
        _tag(session, "t-territoire", "facet-b", label="Territoire")
        _tag(session, "t-retire", "facet-a", active=False)

        vocabulary = load_vocabulary(session)

    assert [t.name for t in vocabulary["facet-a"]] == ["t-usagers"]
    assert [t.name for t in vocabulary["facet-b"]] == ["t-territoire"]


def test_load_vocabulary_can_include_inactive(db):
    with get_db() as session:
        _tag(session, "t-retire", "facet-a", active=False)

        vocabulary = load_vocabulary(session, active_only=False)

    assert [t.name for t in vocabulary["facet-a"]] == ["t-retire"]


def test_load_implications_maps_names(db):
    with get_db() as session:
        siae = _tag(session, "siae", "audience")
        solutions = _tag(session, "solutions-structurees", "audience")
        session.add(TagImplication(tag_id=siae.id, implies_tag_id=solutions.id))
        session.flush()

        assert load_implications(session) == {"siae": {"solutions-structurees"}}
