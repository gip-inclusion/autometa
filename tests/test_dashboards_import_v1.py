"""Tests for the V1 importer's normalisation/tolerance logic."""

import pytest

from lib.dashboards_import_v1 import _parse_raw_fm, _to_bool, _v1_canonical_tag


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("appli", None),
        ("dashboard", None),
        ("dev", None),
        ("metabase", None),
        ("contact", "contacts"),
        ("orientations", "orientation"),
        ("rétention", "retention"),
        ("cross-produit", "multi-produits"),
        ("multi", "multi-produits"),
        ("CLPE", "clpe"),
        ("SIAE", "siae"),
        ("taux retour", "taux-retour"),
        ("foo", "foo"),
        ("", None),
    ],
)
def test_v1_canonical_tag(raw, expected):
    assert _v1_canonical_tag(raw) == expected


@pytest.mark.parametrize(
    ("content", "expected_keys"),
    [
        ("no frontmatter at all", set()),
        ("---\nincomplete frontmatter", set()),
        ("---\ntitle: x\ncron: true\n---\nbody", {"title", "cron"}),
    ],
)
def test_parse_raw_fm_tolerates_malformed(content, expected_keys):
    assert set(_parse_raw_fm(content).keys()) == expected_keys


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", False),
        ("true", True),
        ("True", True),
        ("yes", True),
        ("false", False),
        ("0", False),
        ("off", False),
    ],
)
def test_to_bool(value, expected):
    assert _to_bool(value) == expected
