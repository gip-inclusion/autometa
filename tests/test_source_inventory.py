"""Collecte et stockage de l'inventaire des sources — lib/source_inventory.py."""

import httpx
import pytest
from sqlalchemy import delete, select

from lib import source_inventory
from lib.source_inventory import InventoryItem, refresh_all, replace_inventory
from web.db import get_db
from web.models import SourceInventoryItem, SourceInventoryRun

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]


def item(external_id="1", label="Un élément", item_type="page"):
    return InventoryItem(item_type=item_type, external_id=external_id, label=label)


def stored(source):
    with get_db() as session:
        return sorted(
            (r.external_id, r.label)
            for r in session.scalars(select(SourceInventoryItem).where(SourceInventoryItem.source == source))
        )


def run_row(source):
    """Le run sous forme de tuple : la ligne ORM se détache dès la sortie de session."""
    with get_db() as session:
        row = session.scalar(select(SourceInventoryRun).where(SourceInventoryRun.source == source))
        return (row.last_success_at, row.item_count, row.last_error) if row else None


@pytest.fixture(autouse=True)
def clear_inventory_tables():
    """La fixture `_db` ne vide pas les tables entre deux tests — ces deux-là doivent l'être."""
    yield
    with get_db() as session:
        session.execute(delete(SourceInventoryItem))
        session.execute(delete(SourceInventoryRun))


def test_inventory_is_stored_and_dated():
    replace_inventory("notion", [item("a", "Base A"), item("b", "Base B")])

    assert stored("notion") == [("a", "Base A"), ("b", "Base B")]
    success_at, count, _ = run_row("notion")
    assert success_at is not None
    assert count == 2


def test_a_refresh_replaces_what_disappeared_upstream():
    replace_inventory("notion", [item("a", "Base A"), item("b", "Base B")])
    replace_inventory("notion", [item("a", "Base A renommée")])

    assert stored("notion") == [("a", "Base A renommée")]


def test_one_failing_connector_does_not_stop_the_others(mocker):
    """DOD-3 : les autres aboutissent, et le compte rendu nomme celui qui a échoué."""
    mocker.patch.dict(
        source_inventory.CONNECTORS,
        {
            "notion": lambda: (_ for _ in ()).throw(httpx.ConnectError("injoignable")),
            "tally": lambda: [item("w1", "Espace", item_type="workspace")],
        },
        clear=True,
    )

    report = refresh_all()

    assert report["notion"].startswith("ÉCHEC")
    assert report["tally"] == "1 éléments"
    assert stored("tally") == [("w1", "Espace")]


def test_a_failure_keeps_the_previous_inventory_and_its_date():
    """DOD-4 : un échec ne vide jamais une source."""
    replace_inventory("notion", [item("a", "Base A")])
    first_success, _, _ = run_row("notion")

    source_inventory.record_failure("notion", "ConnectError: injoignable")

    after_success, _, error = run_row("notion")
    assert stored("notion") == [("a", "Base A")]
    assert after_success == first_success
    assert "injoignable" in error


def test_the_freshness_signal_follows_the_last_success_not_the_last_attempt():
    """DOD-10 : la date affichée est celle d'un succès."""
    replace_inventory("tally", [item("w1", "Espace", item_type="workspace")])
    success = source_inventory.last_success("tally")

    source_inventory.record_failure("tally", "HTTPError: 503")

    assert source_inventory.last_success("tally") == success


def test_a_source_never_refreshed_has_no_date():
    assert source_inventory.last_success("notion") is None


def test_notion_collects_roots_but_not_nested_pages(mocker):
    """DOD-5 : seules les racines — une page rangée dans une base n'est pas un point d'entrée."""
    mocker.patch.object(
        source_inventory,
        "notion_request",
        return_value={
            "has_more": False,
            "results": [
                {
                    "object": "database",
                    "id": "db-1",
                    "parent": {"type": "workspace"},
                    "url": "https://notion.so/db-1",
                    "title": [{"plain_text": "Suivi"}],
                },
                {
                    "object": "page",
                    "id": "page-nested",
                    "parent": {"type": "database_id", "database_id": "db-1"},
                    "url": "https://notion.so/page-nested",
                },
            ],
        },
    )

    roots = source_inventory.fetch_notion_roots()

    assert [r.external_id for r in roots] == ["db-1"]
    assert roots[0].label == "Suivi"


def test_tally_collects_workspaces_only(mocker):
    """DOD-6 : les espaces, pas les formulaires ni les réponses."""
    response = httpx.Response(
        200,
        json={"items": [{"id": "ws-1", "name": "Équipe"}]},
        request=httpx.Request("GET", "https://api.tally.so/workspaces"),
    )
    mocker.patch.object(httpx, "get", return_value=response)

    workspaces = source_inventory.fetch_tally_workspaces()

    assert [(w.item_type, w.external_id, w.label) for w in workspaces] == [("workspace", "ws-1", "Équipe")]
