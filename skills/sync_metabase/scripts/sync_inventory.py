#!/usr/bin/env python3
"""Sync Metabase cards inventory to PostgreSQL cache tables."""

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from lib.query import MetabaseError
from lib.sources import get_metabase, get_source_config, list_instances
from skills.metabase_query.scripts.cards_db import TOPICS, TABLE_TO_TOPIC
from web.db import get_db
from web.llm import generate_text


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


def categorize_cards_with_llm(cards: list[dict]) -> dict[int, tuple[str, str]]:
    topic_list = "\n".join(f"- {topic}: {desc}" for topic, desc in TOPICS.items())
    results = {}
    batch_size = 15
    total_batches = (len(cards) + batch_size - 1) // batch_size

    for i in range(0, len(cards), batch_size):
        batch_num = i // batch_size + 1
        progress_bar(batch_num - 1, total_batches, prefix="   Categorizing", suffix=f"batch {batch_num}/{total_batches}")
        batch = cards[i : i + batch_size]
        card_summaries = [{"id": c["id"], "title": c["name"], "sql": c.get("sql_query", "")[:800]} for c in batch]

        prompt = f"""Categorize these Metabase cards about French IAE employment data.

Categories:
{topic_list}

Cards:
{json.dumps(card_summaries, indent=2, ensure_ascii=False)}

Return JSON array:
[{{"id": 7090, "topic": "candidatures", "reason": "queries candidature table"}}, ...]

IMPORTANT:
- Use ONLY the topic slugs listed above
- Look at SQL table names and fields to determine the topic
- Every card MUST get a topic - pick the closest match
- For ESAT questionnaire tables, use "esat"
- If unsure, look at what data the card is measuring
"""
        try:
            result_text = generate_text(prompt, max_tokens=4000, timeout=120)
            json_match = re.search(r"\[[\s\S]*\]", result_text)
            if not json_match:
                raise ValueError("No JSON array found in response")
            for item in json.loads(json_match.group()):
                topic = item["topic"]
                if topic not in TOPICS:
                    card_data = next((c for c in batch if c["id"] == item["id"]), None)
                    inferred = infer_topic_from_tables(card_data.get("tables_referenced", [])) if card_data else None
                    topic = inferred or "candidatures"
                results[item["id"]] = (topic, item.get("reason", ""))
        except Exception as e:
            print(f"\n   Warning: batch error: {e}")
            for card in batch:
                inferred = infer_topic_from_tables(card.get("tables_referenced", []))
                results[card["id"]] = (inferred or "candidatures", "inferred from tables")

    progress_bar(total_batches, total_batches, prefix="   Categorizing", suffix=f"batch {total_batches}/{total_batches}")
    return results


def save_to_db(instance: str, cards: list[dict], dashboard_metadata: dict):
    with get_db() as conn:
        conn.execute("DELETE FROM metabase_cards WHERE instance = %s", (instance,))
        conn.execute("DELETE FROM metabase_dashboards WHERE instance = %s", (instance,))

        for card in cards:
            conn.execute(
                """INSERT INTO metabase_cards
                   (id, instance, name, description, collection_id, dashboard_id, dashboard_name,
                    topic, sql_query, tables_json, synced_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
                (card["id"], instance, card["name"], card.get("description"),
                 card.get("collection_id"), card.get("dashboard_id"),
                 dashboard_metadata.get(card.get("dashboard_id"), {}).get("name"),
                 card.get("topic", "candidatures"), card.get("sql_query", ""),
                 json.dumps(card.get("tables_referenced", []))),
            )

        for dash_id, meta in dashboard_metadata.items():
            conn.execute(
                """INSERT INTO metabase_dashboards
                   (id, instance, name, description, topic, pilotage_url, collection_id, synced_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())""",
                (dash_id, instance, meta["name"], meta.get("description"),
                 None, meta.get("pilotage_url"), meta.get("collection_id")),
            )


def sync_instance(instance_name: str, skip_categorize: bool):
    instance_config = get_source_config("metabase", instance_name)
    public_dashboards = instance_config.get("dashboards", {})
    dashboard_ids = list(public_dashboards.keys())

    if not dashboard_ids:
        print(f"  No dashboards configured for instance '{instance_name}'")
        return

    print(f"\n--- Metabase sync: {instance_name} ({len(dashboard_ids)} dashboards) ---")

    try:
        api = get_metabase(instance_name)
    except Exception as e:
        print(f"  Failed to connect: {e}", file=sys.stderr)
        return

    all_cards = []
    seen_card_ids = set()
    dashboard_metadata = {}

    for dash_id in dashboard_ids:
        print(f"  Dashboard {dash_id}...", end=" ", flush=True)
        try:
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
        except MetabaseError as e:
            print(f"Error: {e}")

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

    if skip_categorize:
        for card in all_cards:
            card["topic"] = infer_topic_from_tables(card.get("tables_referenced", [])) or "candidatures"
    else:
        categorizations = categorize_cards_with_llm(all_cards)
        for card in all_cards:
            topic, _ = categorizations.get(card["id"], (None, ""))
            if not topic or topic not in TOPICS:
                topic = infer_topic_from_tables(card.get("tables_referenced", [])) or "candidatures"
            card["topic"] = topic

    save_to_db(instance_name, all_cards, dashboard_metadata)
    print(f"  Saved {len(all_cards)} cards + {len(dashboard_metadata)} dashboards to PostgreSQL")


def main():
    parser = argparse.ArgumentParser(description="Sync Metabase cards to PostgreSQL")
    parser.add_argument("--instance", type=str)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--skip-categorize", action="store_true")
    args = parser.parse_args()

    if not args.instance and not args.all:
        available = list_instances("metabase")
        print(f"Error: --instance <name> or --all required. Available: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)

    instances = list_instances("metabase") if args.all else [args.instance]
    for instance_name in instances:
        sync_instance(instance_name, args.skip_categorize)

    print("\nDone.")


if __name__ == "__main__":
    main()
