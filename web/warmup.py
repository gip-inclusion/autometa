"""Generate cache files from PostgreSQL for the agent to read.

Called at startup (entrypoint.sh) and after sync cron jobs.
Writes to DATA_DIR/cache/ which is ephemeral and not git-tracked.
"""

import json
import logging

from . import config
from .db import get_db
from .schema import init_db

logger = logging.getLogger(__name__)

CACHE_DIR = config.DATA_DIR / "cache"


def warmup_matomo_baselines():
    with get_db() as conn:
        sites = conn.execute("SELECT DISTINCT site_id FROM matomo_baselines ORDER BY site_id").fetchall()

    if not sites:
        logger.info("No matomo baselines in DB, skipping")
        return

    out_dir = CACHE_DIR / "matomo"
    out_dir.mkdir(parents=True, exist_ok=True)

    for site_row in sites:
        site_id = site_row["site_id"]
        with get_db() as conn:
            baselines = conn.execute(
                "SELECT * FROM matomo_baselines WHERE site_id = %s ORDER BY month", (site_id,)
            ).fetchall()
            dimensions = conn.execute(
                "SELECT * FROM matomo_dimensions WHERE site_id = %s ORDER BY dimension_id", (site_id,)
            ).fetchall()
            segments = conn.execute(
                "SELECT * FROM matomo_segments WHERE site_id = %s ORDER BY name", (site_id,)
            ).fetchall()
            events = conn.execute(
                "SELECT * FROM matomo_events WHERE site_id = %s ORDER BY event_count DESC LIMIT 50", (site_id,)
            ).fetchall()

        lines = [f"# Matomo Site {site_id} — Cached Data", ""]

        if baselines:
            synced = baselines[0].get("synced_at", "")
            lines += ["## Traffic Baselines", "", f"*Synced: {synced}*", ""]
            lines += ["| Month | Visitors | Visits | Bounce | Actions/Visit | Avg Time |"]
            lines += ["|-------|----------|--------|--------|---------------|----------|"]
            for b in baselines:
                if b.get("visitors") is None:
                    continue
                avg_time = b.get("avg_time_on_site", 0) or 0
                time_str = f"{avg_time // 60}m{avg_time % 60:02d}s" if avg_time else "-"
                lines.append(
                    f"| {b['month']} | {b.get('visitors', '-'):,} | {b.get('visits', '-'):,} "
                    f"| {b.get('bounce_rate', '-')} | {b.get('actions_per_visit', '-')} | {time_str} |"
                )

            if any(b.get("user_types") for b in baselines):
                lines += ["", "### User Types (visits per month)", ""]
                all_types = set()
                for b in baselines:
                    if b.get("user_types"):
                        ut = json.loads(b["user_types"]) if isinstance(b["user_types"], str) else b["user_types"]
                        all_types.update(ut.keys())
                all_types = sorted(all_types)
                if all_types:
                    lines.append("| Month | " + " | ".join(all_types) + " |")
                    lines.append("|-------" + "|-------" * len(all_types) + "|")
                    for b in baselines:
                        ut = {}
                        if b.get("user_types"):
                            ut = json.loads(b["user_types"]) if isinstance(b["user_types"], str) else b["user_types"]
                        lines.append(
                            "| " + b["month"] + " | " + " | ".join(str(ut.get(t, 0)) for t in all_types) + " |"
                        )

        if dimensions:
            lines += ["", "## Custom Dimensions", ""]
            lines += ["| ID | Scope | Name |", "|----|-------|------|"]
            for d in dimensions:
                if d.get("active"):
                    lines.append(f"| {d['dimension_id']} | {d.get('scope', '')} | {d['name']} |")

        if segments:
            lines += ["", "## Saved Segments", ""]
            lines += ["| Name | Definition |", "|------|------------|"]
            for s in segments:
                defn = (s.get("definition") or "")[:60]
                lines.append(f"| {s['name']} | `{defn}` |")

        if events:
            lines += ["", "## Top Events", ""]
            lines += ["| Name | Events | Visits |", "|------|--------|--------|"]
            for e in events:
                lines.append(f"| {e['name']} | {e.get('event_count', 0):,} | {e.get('visit_count', 0):,} |")

        (out_dir / f"site-{site_id}.md").write_text("\n".join(lines) + "\n")

    logger.info(f"Generated {len(sites)} matomo cache files")


def warmup_metabase_cards():
    with get_db() as conn:
        instances = conn.execute("SELECT DISTINCT instance FROM metabase_cards").fetchall()

    if not instances:
        logger.info("No metabase cards in DB, skipping")
        return

    for inst_row in instances:
        instance = inst_row["instance"]
        out_dir = CACHE_DIR / "metabase" / instance
        cards_dir = out_dir / "cards"
        dashboards_dir = out_dir / "dashboards"
        cards_dir.mkdir(parents=True, exist_ok=True)
        dashboards_dir.mkdir(parents=True, exist_ok=True)

        with get_db() as conn:
            topics = conn.execute(
                "SELECT topic, COUNT(*) as n FROM metabase_cards WHERE instance = %s GROUP BY topic ORDER BY n DESC",
                (instance,),
            ).fetchall()

            for topic_row in topics:
                topic = topic_row["topic"]
                cards = conn.execute(
                    "SELECT * FROM metabase_cards WHERE instance = %s AND topic = %s ORDER BY id",
                    (instance, topic),
                ).fetchall()

                lines = [f"# {topic}", "", f"**{len(cards)} cartes**", ""]
                for c in cards:
                    lines.append(f"## [{c['id']}] {c['name']}")
                    if c.get("description"):
                        lines.append(f"\n{c['description']}")
                    if c.get("dashboard_name"):
                        lines.append(f"\n*Dashboard: {c['dashboard_name']}*")
                    if c.get("sql_query"):
                        sql = c["sql_query"][:2000]
                        lines.append(f"\n```sql\n{sql}\n```")
                    lines.append("")

                (cards_dir / f"topic-{topic}.md").write_text("\n".join(lines) + "\n")

            dashboards = conn.execute(
                "SELECT * FROM metabase_dashboards WHERE instance = %s ORDER BY id", (instance,)
            ).fetchall()

            for dash in dashboards:
                cards = conn.execute(
                    "SELECT * FROM metabase_cards WHERE instance = %s AND dashboard_id = %s ORDER BY id",
                    (instance, dash["id"]),
                ).fetchall()
                lines = [f"# Dashboard {dash['id']}: {dash['name']}", ""]
                if dash.get("pilotage_url"):
                    lines.append(f"URL: {dash['pilotage_url']}")
                lines.append(f"\n**{len(cards)} cartes**\n")
                for c in cards:
                    sql_preview = (c.get("sql_query") or "")[:200].replace("\n", " ")
                    lines.append(f"- [{c['id']}] {c['name']} ({c.get('topic', '?')}) — `{sql_preview}`")
                lines.append("")
                (dashboards_dir / f"dashboard-{dash['id']}.md").write_text("\n".join(lines) + "\n")

        logger.info(
            f"Generated metabase cache for instance '{instance}': {len(topics)} topics, {len(dashboards)} dashboards"
        )


def run():
    init_db()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Warming up cache in {CACHE_DIR}")
    warmup_matomo_baselines()
    warmup_metabase_cards()
    logger.info("Warmup complete")


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    run()
