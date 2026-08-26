"""Ce que contient chaque source : lu là où l'inventaire vit déjà, jamais recollecté pour la page."""

import logging
from dataclasses import dataclass

from sqlalchemy import func, select

from lib.query import CallerType, execute_autometa_tables_query
from lib.source_inventory import list_inventory

from .db import get_db
from .models import MatomoDimension, MatomoEvent, MatomoSegment, MetabaseCard, MetabaseDashboard

logger = logging.getLogger(__name__)

CATALOG_SQL = """
    SELECT table_schema, table_name, table_description, column_name, column_type, column_description
    FROM documentation.doc_autometa_tables
    ORDER BY table_schema, table_name, column_name
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
    """Schémas, tables et colonnes lus à l'exécution : la liste n'est jamais écrite en dur."""
    result = execute_autometa_tables_query(CATALOG_SQL, caller=CallerType.APP)
    if not result.success:
        return Inventory(kind="catalog", groups=[], total=0, error=result.error or "catalogue illisible")

    rows = result.data["rows"]
    needle = search.strip().lower()
    tables: dict[tuple[str, str], dict] = {}
    for schema, table, table_desc, column, column_type, column_desc in rows:
        if needle and needle not in f"{schema}.{table} {column}".lower():
            continue
        entry = tables.setdefault(
            (schema, table),
            {"schema": schema, "name": table, "description": table_desc, "columns": []},
        )
        entry["columns"].append({"name": column, "type": column_type, "description": column_desc})

    groups: dict[str, list] = {}
    for (schema, _), entry in sorted(tables.items()):
        groups.setdefault(schema, []).append(entry)

    return Inventory(
        kind="catalog",
        groups=[{"label": schema, "items": items} for schema, items in sorted(groups.items())],
        total=len(tables),
        note="Catalogue lu en direct dans documentation.doc_autometa_tables." if not needle else None,
    )


def metabase_inventory(instance: str) -> Inventory:
    """Cartes et tableaux de bord déjà synchronisés chaque nuit : aucune collecte ajoutée ici."""
    with get_db() as session:
        dashboards = session.scalars(
            select(MetabaseDashboard).where(MetabaseDashboard.instance == instance).order_by(MetabaseDashboard.name)
        ).all()
        card_counts = dict(
            session.execute(
                select(MetabaseCard.topic, func.count())
                .where(MetabaseCard.instance == instance)
                .group_by(MetabaseCard.topic)
            ).all()
        )
        total = session.scalar(select(func.count()).select_from(MetabaseCard).where(MetabaseCard.instance == instance))

    groups = []
    if dashboards:
        groups.append({
            "label": "Tableaux de bord",
            "items": [{"name": d.name, "description": d.description} for d in dashboards],
        })
    if card_counts:
        groups.append({
            "label": "Cartes par thème",
            "items": [
                {"name": topic or "sans thème", "description": f"{count} cartes"}
                for topic, count in sorted(card_counts.items(), key=lambda kv: -kv[1])
            ],
        })
    return Inventory(kind="listing", groups=groups, total=total or 0)


def matomo_inventory() -> Inventory:
    """Dimensions, segments et événements des sites, depuis les tables miroir de sync-sites."""
    with get_db() as session:
        dimensions = session.scalars(select(MatomoDimension).order_by(MatomoDimension.site_id)).all()
        segments = session.scalars(select(MatomoSegment).order_by(MatomoSegment.site_id)).all()
        top_events = session.execute(
            select(MatomoEvent.name, func.sum(MatomoEvent.event_count).label("total"))
            .group_by(MatomoEvent.name)
            .order_by(func.sum(MatomoEvent.event_count).desc())
            .limit(25)
        ).all()

    groups = []
    if dimensions:
        groups.append({
            "label": "Dimensions personnalisées",
            "items": [{"name": d.name, "description": f"site {d.site_id} · {d.scope or 'visite'}"} for d in dimensions],
        })
    if segments:
        groups.append({
            "label": "Segments enregistrés",
            "items": [{"name": s.name, "description": f"site {s.site_id}"} for s in segments],
        })
    if top_events:
        groups.append({
            "label": "Événements les plus fréquents",
            "items": [
                {"name": name, "description": f"{total:,} événements".replace(",", " ")} for name, total in top_events
            ],
        })
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
    if slug.startswith("metabase-"):
        return metabase_inventory(slug.removeprefix("metabase-").replace("-", "_"))
    if slug in ("notion", "tally"):
        return connector_inventory(slug)
    return None
