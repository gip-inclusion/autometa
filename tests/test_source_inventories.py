"""Panneaux d'inventaire des pages /sources/<slug> — web/source_inventories.py."""

import pytest

from lib.query import QueryResult
from web import source_inventories
from web.source_inventories import autometa_tables_catalog, inventory_for

CATALOG_ROWS = [
    ["candidatures", "Les candidatures", "id", "text", "Identifiant"],
    ["candidatures", "Les candidatures", "created_at", "text", "Date ISO"],
    ["table_arrivee_apres_coup", "Inconnue du code", "col", "int", None],
]


def catalog_result(rows=None, success=True, error=None):
    return QueryResult(
        success=success,
        data={"columns": [], "rows": rows or [], "row_count": len(rows or [])},
        error=error,
    )


def test_catalog_lists_tables_with_their_columns(mocker):
    """DOD-7 : tables et colonnes, avec leurs descriptions."""
    mocker.patch.object(source_inventories, "execute_autometa_tables_query", return_value=catalog_result(CATALOG_ROWS))

    inventory = autometa_tables_catalog()

    assert inventory.total == 2
    table = inventory.groups[0]["items"][0]
    assert table["name"] == "candidatures"
    assert table["description"] == "Les candidatures"
    assert [c["name"] for c in table["columns"]] == ["id", "created_at"]


def test_catalog_shows_a_table_the_code_has_never_heard_of(mocker):
    """DOD-8 : le catalogue est lu à l'exécution — le changement de base source est transparent."""
    mocker.patch.object(source_inventories, "execute_autometa_tables_query", return_value=catalog_result(CATALOG_ROWS))

    names = [t["name"] for t in autometa_tables_catalog().groups[0]["items"]]
    assert "table_arrivee_apres_coup" in names


@pytest.mark.parametrize(
    "search,expected",
    [("candidat", ["candidatures"]), ("created_at", ["candidatures"]), ("introuvable", [])],
)
def test_catalog_filters_by_table_or_column(mocker, search, expected):
    mocker.patch.object(source_inventories, "execute_autometa_tables_query", return_value=catalog_result(CATALOG_ROWS))

    groups = autometa_tables_catalog(search).groups
    found = [t["name"] for t in groups[0]["items"]] if groups else []
    assert found == expected


def test_catalog_reports_an_unreachable_source_without_raising(mocker):
    mocker.patch.object(
        source_inventories,
        "execute_autometa_tables_query",
        return_value=catalog_result(success=False, error="connexion refusée"),
    )

    inventory = autometa_tables_catalog()

    assert inventory.error == "connexion refusée"
    assert inventory.groups == []


@pytest.mark.parametrize("slug", ["s3", "slack", "rpe", "inexistante"])
def test_sources_without_an_inventory_return_none(slug):
    assert inventory_for(slug) is None


@pytest.mark.integration
@pytest.mark.usefixtures("_db")
@pytest.mark.parametrize("slug", ["metabase-stats", "matomo", "notion"])
def test_db_backed_inventories_are_readable_outside_the_session(slug):
    """Ces panneaux lisent des lignes ORM : les valeurs doivent être extraites dans la session, sinon 500."""
    from sqlalchemy import delete

    from lib.source_inventory import InventoryItem, replace_inventory
    from web.db import get_db
    from web.models import MatomoDimension, MetabaseCard, SourceInventoryItem, SourceInventoryRun

    with get_db() as session:
        # Why: la fixture `_db` ne vide pas les tables entre deux paramètres — sans quoi, doublon en insertion.
        session.execute(delete(MetabaseCard))
        session.execute(delete(MatomoDimension))
        session.execute(delete(SourceInventoryItem))
        session.execute(delete(SourceInventoryRun))
        session.add(MetabaseCard(id=1, instance="stats", name="Une carte", topic="candidatures"))
        session.add(MatomoDimension(site_id=117, dimension_id=1, name="UserKind", scope="visit"))
    replace_inventory("notion", [InventoryItem(item_type="database", external_id="db-1", label="Suivi")])

    inventory = inventory_for(slug)

    assert inventory.groups, "un inventaire peuplé doit rendre au moins un groupe"
    for group in inventory.groups:
        for entry in group["items"]:
            assert entry["name"] is not None
