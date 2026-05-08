"""Tests for the alembic data import migration's V1 logic (canonicalisation, tolerance)."""

import importlib.util
from pathlib import Path

import pytest

_MIGRATION_PATH = Path("alembic/versions/d37119f978f5_dashboards_import.py")


@pytest.fixture(scope="module")
def migration():
    spec = importlib.util.spec_from_file_location("dashboards_import_migration", _MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
def test_v1_canonical_tag(migration, raw, expected):
    assert migration._v1_canonical_tag(raw) == expected


@pytest.mark.parametrize(
    ("content", "expected_keys"),
    [
        ("no frontmatter at all", set()),
        ("---\nincomplete frontmatter", set()),
        ("---\ntitle: x\ncron: true\n---\nbody", {"title", "cron"}),
    ],
)
def test_parse_raw_fm_tolerates_malformed(migration, content, expected_keys):
    assert set(migration._parse_raw_fm(content).keys()) == expected_keys


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
def test_to_bool(migration, value, expected):
    assert migration._to_bool(value) == expected
