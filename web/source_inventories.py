"""Ce que contient chaque source : lu là où l'inventaire vit déjà, jamais recollecté pour la page."""

import logging
from dataclasses import dataclass

from sqlalchemy import func, select

from lib.query import CallerType, execute_autometa_tables_query
from lib.source_inventory import list_inventory

from .db import get_db
from .models import MatomoDimension, MatomoEvent, MatomoSegment

logger = logging.getLogger(__name__)

CATALOG_SQL = """
    SELECT table_id, table_name, table_description, column_name, column_type, column_description
    FROM documentation.doc_autometa_tables
    ORDER BY table_name, table_id, column_name
"""


@dataclass(frozen=True)
class Inventory:
    """Un inventaire affichable : des groupes nommés, chacun listant des entrées."""

    kind: str
    groups: list[dict]
    total: int
    note: str | None = None
    error: str | None = None


def autometa_tables_catalog(search: str = "") -> Inventory:
    """Tables et colonnes lues à l'exécution : rien n'est écrit en dur, le catalogue fait foi."""
    # Why: l'identité d'une table est `table_id`, pas son nom — 71 tables documentées ne portent que
    # 34 noms distincts (`users_user` en désigne quatre). Grouper par nom fusionnerait leurs colonnes.
    # Le catalogue ne porte pas de schéma, et le déduire des jeux de colonnes n'en résout que 26 sur 71.
    result = execute_autometa_tables_query(CATALOG_SQL, caller=CallerType.APP)
    if not result.success:
        return Inventory(kind="catalog", groups=[], total=0, error=result.error or "catalogue illisible")

    needle = search.strip().lower()
    tables: dict[int, dict] = {}
    for table_id, table, table_desc, column, column_type, column_desc in result.data["rows"]:
        if needle and needle not in f"{table} {column}".lower():
            continue
        entry = tables.setdefault(table_id, {"id": table_id, "name": table, "description": table_desc, "columns": []})
        entry["columns"].append({"name": column, "type": column_type, "description": column_desc})

    ordered = sorted(tables.values(), key=lambda t: (t["name"], t["id"]))
    groups = [{"label": "Tables", "items": ordered}] if ordered else []
    return Inventory(
        kind="catalog",
        groups=groups,
        total=len(tables),
        note="Catalogue lu en direct dans documentation.doc_autometa_tables." if not needle else None,
    )


def matomo_inventory() -> Inventory:
    """Dimensions, segments et événements des sites, depuis les tables miroir de sync-sites."""
    with get_db() as session:
        dimensions = [
            {"name": d.name, "description": f"site {d.site_id} · {d.scope or 'visite'}"}
            for d in session.scalars(select(MatomoDimension).order_by(MatomoDimension.site_id))
        ]
        segments = [
            {"name": seg.name, "description": f"site {seg.site_id}"}
            for seg in session.scalars(select(MatomoSegment).order_by(MatomoSegment.site_id))
        ]
        top_events = [
            {"name": name, "description": f"{total:,} événements".replace(",", " ")}
            for name, total in session.execute(
                select(MatomoEvent.name, func.sum(MatomoEvent.event_count))
                .group_by(MatomoEvent.name)
                .order_by(func.sum(MatomoEvent.event_count).desc())
                .limit(25)
            )
        ]

    groups = [
        {"label": label, "items": items}
        for label, items in (
            ("Dimensions personnalisées", dimensions),
            ("Segments enregistrés", segments),
            ("Événements les plus fréquents", top_events),
        )
        if items
    ]
    return Inventory(kind="listing", groups=groups, total=len(dimensions) + len(segments))


def connector_inventory(source: str) -> Inventory:
    """Racines Notion, espaces Tally… collectés par sync-connectors."""
    rows = list_inventory(source)
    groups: dict[str, list] = {}
    for row in rows:
        # Why: un identifiant Notion n'apprend rien à un lecteur — mieux vaut dire que le titre manque.
        groups.setdefault(row.item_type, []).append({
            "name": row.label or "sans titre",
            "description": None,
            "url": row.url,
        })
    return Inventory(
        kind="listing",
        groups=[{"label": label, "items": items} for label, items in sorted(groups.items())],
        total=len(rows),
    )


def inventory_for(slug: str, search: str = "") -> Inventory | None:
    if slug == "autometa-tables-db":
        return autometa_tables_catalog(search)
    if slug == "matomo":
        return matomo_inventory()
    if slug in ("notion", "tally"):
        return connector_inventory(slug)
    return None
