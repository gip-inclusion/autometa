"""Inventaire des sources : le sommaire de ce qu'elles contiennent, rafraîchi périodiquement."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from web import config
from web.db import get_db
from web.models import SourceInventoryItem, SourceInventoryRun

from .notion import extract_text_from_rich_text, notion_request

logger = logging.getLogger(__name__)

FETCH_TIMEOUT_SEC = 15
NOTION_PAGE_SIZE = 100


@dataclass(frozen=True)
class InventoryItem:
    item_type: str
    external_id: str
    label: str | None = None
    parent_external_id: str | None = None
    url: str | None = None
    extra: dict | None = None


def notion_parent_id(result: dict) -> str | None:
    parent = result.get("parent", {})
    kind = parent.get("type")
    return parent.get(kind) if kind and kind != "workspace" else None


def is_share_root(result: dict, accessible: set[str]) -> bool:
    """Vrai quand l'accès commence ici : le parent n'est pas lui-même une page ou une base visible."""
    return notion_parent_id(result) not in accessible


def fetch_notion_roots() -> list[InventoryItem]:
    """Les points où l'intégration a été ajoutée — l'accès est hérité, le reste est du contenu."""
    # Why: l'API n'expose pas « où le partage a été fait ». On l'en déduit : la recherche ne renvoie que
    # ce que l'intégration voit, donc un objet dont le parent n'y figure pas est un point de partage.
    # Réserve mesurée : 98 des 112 racines ont un bloc pour parent, et un bloc peut appartenir à une page
    # visible — remonter la chaîne coûte plusieurs appels par objet et se heurte à des 404. Ces objets
    # sont donc conservés, au risque d'en garder quelques-uns qui ne sont pas de vrais points de partage.
    objects: dict[str, dict] = {}
    cursor = None
    while True:
        payload: dict = {"page_size": NOTION_PAGE_SIZE}
        if cursor:
            payload["start_cursor"] = cursor
        data = notion_request("POST", "search", payload)
        for result in data.get("results", []):
            objects[result["id"]] = result
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

    accessible = set(objects)
    return [
        InventoryItem(
            item_type=result.get("object", "page"),
            external_id=result["id"],
            label=notion_title(result),
            parent_external_id=notion_parent_id(result),
            url=result.get("url"),
        )
        for result in objects.values()
        if is_share_root(result, accessible)
    ]


def notion_title(result: dict) -> str | None:
    """Le titre d'une base est dans `title` ; celui d'une page, dans la propriété de type title."""
    direct = extract_text_from_rich_text(result.get("title") or []).strip()
    if direct:
        return direct
    for prop in (result.get("properties") or {}).values():
        # Why: sur une base, `properties` décrit le schéma et `title` y vaut {} — d'où le test de type.
        if prop.get("type") == "title" and isinstance(prop.get("title"), list):
            named = extract_text_from_rich_text(prop["title"]).strip()
            if named:
                return named
    return None


def fetch_tally_workspaces() -> list[InventoryItem]:
    """Espaces de travail seulement : descendre aux formulaires transformerait un sommaire en copie."""
    resp = httpx.get(
        "https://api.tally.so/workspaces",
        headers={"Authorization": f"Bearer {config.TALLY_API_KEY}"},
        timeout=FETCH_TIMEOUT_SEC,
    )
    resp.raise_for_status()
    payload = resp.json()
    workspaces = payload.get("items", payload) if isinstance(payload, dict) else payload
    return [
        InventoryItem(
            item_type="workspace",
            external_id=str(w["id"]),
            label=w.get("name"),
            url=f"https://tally.so/workspaces/{w['id']}",
        )
        for w in workspaces
    ]


CONNECTORS = {
    "notion": fetch_notion_roots,
    "tally": fetch_tally_workspaces,
}


def replace_inventory(source: str, items: list[InventoryItem]) -> None:
    """Remplace l'inventaire d'une source. Jamais appelé quand la collecte a échoué."""
    now = datetime.now(timezone.utc)
    with get_db() as session:
        keys = {(i.item_type, i.external_id) for i in items}
        for row in session.scalars(select(SourceInventoryItem).where(SourceInventoryItem.source == source)):
            if (row.item_type, row.external_id) not in keys:
                session.delete(row)
        for item in items:
            session.execute(
                pg_insert(SourceInventoryItem)
                .values(
                    source=source,
                    item_type=item.item_type,
                    external_id=item.external_id,
                    label=item.label,
                    parent_external_id=item.parent_external_id,
                    url=item.url,
                    extra=item.extra,
                    synced_at=now,
                )
                .on_conflict_do_update(
                    constraint="uq_source_inventory_items_identity",
                    set_={
                        "label": item.label,
                        "parent_external_id": item.parent_external_id,
                        "url": item.url,
                        "extra": item.extra,
                        "synced_at": now,
                    },
                )
            )
        record_run(session, source, success_at=now, item_count=len(items))


def record_run(
    session, source: str, success_at: datetime | None, item_count: int = 0, error: str | None = None
) -> None:
    now = datetime.now(timezone.utc)
    values = {"source": source, "last_attempt_at": now, "last_error": error}
    if success_at is not None:
        values |= {"last_success_at": success_at, "item_count": item_count}
    session.execute(
        pg_insert(SourceInventoryRun)
        .values(**values)
        .on_conflict_do_update(index_elements=["source"], set_={k: v for k, v in values.items() if k != "source"})
    )


def record_failure(source: str, error: str) -> None:
    """L'inventaire précédent reste en place : un échec ne vide jamais une source."""
    with get_db() as session:
        record_run(session, source, success_at=None, error=error)


def refresh(source: str) -> int:
    items = CONNECTORS[source]()
    replace_inventory(source, items)
    return len(items)


def refresh_all() -> dict[str, str]:
    """Rafraîchit chaque connecteur. Un échec n'empêche pas les autres et est nommé dans le compte rendu."""
    report: dict[str, str] = {}
    for source in CONNECTORS:
        try:
            report[source] = f"{refresh(source)} éléments"
        except Exception as exc:
            # Why: chaque connecteur a sa propre famille d'erreurs (HTTP, schéma, quota) et ne doit pas
            # emporter les autres — l'inventaire précédent de cette source reste affiché.
            logger.warning("Inventaire %s en échec : %s", source, type(exc).__name__)
            record_failure(source, f"{type(exc).__name__}: {exc}"[:500])
            report[source] = f"ÉCHEC ({type(exc).__name__})"
    return report


def list_inventory(source: str) -> list[SourceInventoryItem]:
    with get_db() as session:
        rows = session.scalars(
            select(SourceInventoryItem)
            .where(SourceInventoryItem.source == source)
            .order_by(SourceInventoryItem.item_type, SourceInventoryItem.label)
        ).all()
        session.expunge_all()
        return list(rows)


def last_success(source: str) -> datetime | None:
    with get_db() as session:
        return session.scalar(select(SourceInventoryRun.last_success_at).where(SourceInventoryRun.source == source))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    report = refresh_all()
    for source, outcome in report.items():
        print(f"{source} : {outcome}")
    if any(o.startswith("ÉCHEC") for o in report.values()):
        raise SystemExit(1)
