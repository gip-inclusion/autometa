"""Panneaux d'inventaire des pages /sources/<slug> — web/source_inventories.py."""

import pytest

from lib.query import QueryResult
from web import source_inventories
from web.source_inventories import autometa_tables_catalog, inventory_for

CATALOG_ROWS = [
    ["les_emplois", "candidatures", "Les candidatures", "id", "text", "Identifiant"],
    ["les_emplois", "candidatures", "Les candidatures", "created_at", "text", "Date ISO"],
    ["schema_inconnu_du_code", "nouvelle_table", "Arrivée après coup", "col", "int", None],
]


def catalog_result(rows=None, success=True, error=None):
    return QueryResult(
        success=success,
        data={"columns": [], "rows": rows or [], "row_count": len(rows or [])},
        error=error,
    )


def test_catalog_groups_tables_by_schema(mocker):
    """DOD-7 : schémas, tables et colonnes, avec leurs descriptions."""
    mocker.patch.object(source_inventories, "execute_autometa_tables_query", return_value=catalog_result(CATALOG_ROWS))

    inventory = autometa_tables_catalog()

    assert [g["label"] for g in inventory.groups] == ["les_emplois", "schema_inconnu_du_code"]
    table = inventory.groups[0]["items"][0]
    assert table["name"] == "candidatures"
    assert table["description"] == "Les candidatures"
    assert [c["name"] for c in table["columns"]] == ["id", "created_at"]


def test_catalog_shows_a_schema_the_code_has_never_heard_of(mocker):
    """DOD-8 : la liste des schémas est lue à l'exécution — le changement de base source est transparent."""
    mocker.patch.object(source_inventories, "execute_autometa_tables_query", return_value=catalog_result(CATALOG_ROWS))

    assert "schema_inconnu_du_code" in [g["label"] for g in autometa_tables_catalog().groups]


@pytest.mark.parametrize(
    "search,expected",
    [("candidat", ["les_emplois"]), ("created_at", ["les_emplois"]), ("introuvable", [])],
)
def test_catalog_filters_by_table_or_column(mocker, search, expected):
    mocker.patch.object(source_inventories, "execute_autometa_tables_query", return_value=catalog_result(CATALOG_ROWS))

    assert [g["label"] for g in autometa_tables_catalog(search).groups] == expected


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
