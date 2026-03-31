#!/usr/bin/env python3
"""Sync Metabase cards inventory to PostgreSQL cache tables."""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import delete

from lib.query import MetabaseError
from lib.sources import get_metabase, get_source_config, list_instances
from skills.metabase_query.scripts.cards_db import TABLE_TO_TOPIC
from web.db import get_db
from web.models import MetabaseCard, MetabaseDashboard


def infer_topic_from_tables(tables: list[str]) -> str | None:
    for table in tables:
        table_lower = table.lower()
        for pattern, topic in TABLE_TO_TOPIC.items():
            if pattern in table_lower:
                return topic
    return None


def progress_bar(current: int, total: int, prefix: str = "", suffix: str = "", length: int = 40):
    if total == 0:
        return
    percent = 100 * current / total
    filled = int(length * current // total)
    bar = "\u2588" * filled + "\u2591" * (length - filled)
    print(f"\r{prefix} |{bar}| {percent:.1f}% {suffix}", end="", flush=True)
    if current == total:
        print()


def extract_table_references(sql: str) -> list[str]:
    if not sql:
        return []
    tables = set()
    patterns = [
        r'FROM\s+"?(\w+)"?\."?(\w+)"?',
        r'FROM\s+"?(\w+)"?(?:\s|$|,)',
        r'JOIN\s+"?(\w+)"?\."?(\w+)"?',
        r'JOIN\s+"?(\w+)"?(?:\s|$)',
    ]
    skip_words = {"select", "case", "when", "then", "else", "end", "as", "on", "and", "or"}
    for pattern in patterns:
        for match in re.findall(pattern, sql, re.IGNORECASE):
            table = ([m for m in match if m][-1] if isinstance(match, tuple) else match)
            if table and table.lower() not in skip_words:
                tables.add(table)
    return sorted(tables)


def save_to_db(instance: str, cards: list[dict], dashboard_metadata: dict):
    with get_db() as session:
        session.execute(delete(MetabaseCard).where(MetabaseCard.instance == instance))
        session.execute(delete(MetabaseDashboard).where(MetabaseDashboard.instance == instance))

        session.add_all([
            MetabaseCard(
                id=card["id"],
                instance=instance,
                name=card["name"],
                description=card.get("description"),
                collection_id=card.get("collection_id"),
                dashboard_id=card.get("dashboard_id"),
                dashboard_name=dashboard_metadata.get(card.get("dashboard_id"), {}).get("name"),
                topic=card.get("topic", "candidatures"),
                sql_query=card.get("sql_query", ""),
                tables_json=json.dumps(card.get("tables_referenced", [])),
            )
            for card in cards
        ])

        session.add_all([
            MetabaseDashboard(
                id=dash_id,
                instance=instance,
                name=meta["name"],
                description=meta.get("description"),
                topic=None,
                pilotage_url=meta.get("pilotage_url"),
                collection_id=meta.get("collection_id"),
            )
            for dash_id, meta in dashboard_metadata.items()
        ])


def sync_instance(instance_name: str):
    instance_config = get_source_config("metabase", instance_name)
    public_dashboards = instance_config.get("dashboards", {})
    dashboard_ids = list(public_dashboards.keys())

    if not dashboard_ids:
        print(f"  No dashboards configured for '{instance_name}'")
        return

    print(f"\n--- Metabase sync: {instance_name} ({len(dashboard_ids)} dashboards) ---")

    api = get_metabase(instance_name)

    all_cards = []
    seen_card_ids = set()
    dashboard_metadata = {}

    for dash_id in dashboard_ids:
        print(f"  Dashboard {dash_id}...", end=" ", flush=True)
        dashboard = api.get_dashboard(dash_id)
        dashboard_metadata[dash_id] = {
            "name": dashboard.get("name", f"Dashboard {dash_id}"),
            "description": dashboard.get("description"),
            "collection_id": dashboard.get("collection_id"),
            "pilotage_url": public_dashboards.get(dash_id),
        }
        for dc in dashboard.get("dashcards", []):
            card = dc.get("card")
            if not card or not card.get("id") or card["id"] in seen_card_ids:
                continue
            name = (card.get("name") or "").strip()
            if not name or re.match(r"^Card \d+$", name):
                continue
            seen_card_ids.add(card["id"])
            all_cards.append({
                "id": card["id"],
                "name": name,
                "description": card.get("description"),
                "collection_id": card.get("collection_id"),
                "dashboard_id": dash_id,
            })
        print(f"{len([c for c in all_cards if c.get('dashboard_id') == dash_id])} cards")

    print(f"  Total: {len(all_cards)} unique cards")

    if not all_cards:
        return

    print("  Fetching SQL queries...", flush=True)

    def fetch_sql(card):
        try:
            sql = api.get_card_sql(card["id"])
            return (card["id"], sql, extract_table_references(sql))
        except (MetabaseError, TimeoutError, OSError):
            return (card["id"], "", [])

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_sql, c): c for c in all_cards}
        completed = 0
        for future in as_completed(futures):
            card_id, sql, tables = future.result()
            for card in all_cards:
                if card["id"] == card_id:
                    card["sql_query"] = sql
                    card["tables_referenced"] = tables
                    break
            completed += 1
            progress_bar(completed, len(all_cards), prefix="  Progress", suffix=f"{completed}/{len(all_cards)}")

    has_sql = sum(1 for c in all_cards if c.get("sql_query"))
    print(f"  SQL: {has_sql}/{len(all_cards)} cards")

    for card in all_cards:
        card["topic"] = infer_topic_from_tables(card.get("tables_referenced", [])) or "candidatures"

    save_to_db(instance_name, all_cards, dashboard_metadata)
    print(f"  Saved {len(all_cards)} cards + {len(dashboard_metadata)} dashboards to PostgreSQL")


def main():
    for instance_name in list_instances("metabase"):
        sync_instance(instance_name)

    print("Done.")


if __name__ == "__main__":
    main()
