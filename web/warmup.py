"""Generate cache files from PostgreSQL for the agent to read.

Called at startup (FastAPI lifespan) and after sync cron jobs.
Writes to DATA_DIR/cache/ which is ephemeral and not git-tracked.
"""

import json
import logging
import time

from sqlalchemy import func, select

from . import config
from .db import get_db
from .models import MatomoBaseline, MatomoDimension, MatomoEvent, MatomoSegment, MetabaseCard, MetabaseDashboard
from .schema import init_db

logger = logging.getLogger(__name__)

CACHE_DIR = config.DATA_DIR / "cache"


def warmup_matomo_baselines():
    out_dir = CACHE_DIR / "matomo"
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    with get_db() as session:
        site_ids = session.scalars(select(MatomoBaseline.site_id).distinct().order_by(MatomoBaseline.site_id)).all()

        for site_id in site_ids:
            baselines = session.scalars(
                select(MatomoBaseline).where(MatomoBaseline.site_id == site_id).order_by(MatomoBaseline.month)
            ).all()
            dimensions = session.scalars(
                select(MatomoDimension).where(MatomoDimension.site_id == site_id).order_by(MatomoDimension.dimension_id)
            ).all()
            segments = session.scalars(
                select(MatomoSegment).where(MatomoSegment.site_id == site_id).order_by(MatomoSegment.name)
            ).all()
            events = session.scalars(
                select(MatomoEvent)
                .where(MatomoEvent.site_id == site_id)
                .order_by(MatomoEvent.event_count.desc())
                .limit(50)
            ).all()

            lines = [f"# Matomo Site {site_id} — Cached Data", ""]

            if baselines:
                synced = baselines[0].synced_at or ""
                lines += ["## Traffic Baselines", "", f"*Synced: {synced}*", ""]
                lines += ["| Month | Visitors | Visits | Bounce | Actions/Visit | Avg Time |"]
                lines += ["|-------|----------|--------|--------|---------------|----------|"]
                for b in baselines:
                    if b.visitors is None:
                        continue
                    avg_time = b.avg_time_on_site or 0
                    time_str = f"{avg_time // 60}m{avg_time % 60:02d}s" if avg_time else "-"
                    lines.append(
                        f"| {b.month} | {b.visitors:,} | {b.visits:,} "
                        f"| {b.bounce_rate or '-'} | {b.actions_per_visit or '-'} | {time_str} |"
                    )

                if any(b.user_types for b in baselines):
                    lines += ["", "### User Types (visits per month)", ""]
                    all_types = set()
                    for b in baselines:
                        if b.user_types:
                            ut = json.loads(b.user_types) if isinstance(b.user_types, str) else b.user_types
                            all_types.update(ut.keys())
                    all_types = sorted(all_types)
                    if all_types:
                        lines.append("| Month | " + " | ".join(all_types) + " |")
                        lines.append("|-------" + "|-------" * len(all_types) + "|")
                        for b in baselines:
                            ut = {}
                            if b.user_types:
                                ut = json.loads(b.user_types) if isinstance(b.user_types, str) else b.user_types
                            lines.append(
                                "| " + b.month + " | " + " | ".join(str(ut.get(t, 0)) for t in all_types) + " |"
                            )

            if dimensions:
                lines += ["", "## Custom Dimensions", ""]
                lines += ["| ID | Scope | Name |", "|----|-------|------|"]
                for d in dimensions:
                    if d.active:
                        lines.append(f"| {d.dimension_id} | {d.scope or ''} | {d.name} |")

            if segments:
                lines += ["", "## Saved Segments", ""]
                lines += ["| Name | Definition |", "|------|------------|"]
                for s in segments:
                    defn = (s.definition or "")[:60]
                    lines.append(f"| {s.name} | `{defn}` |")

            if events:
                lines += ["", "## Top Events", ""]
                lines += ["| Name | Events | Visits |", "|------|--------|--------|"]
                for e in events:
                    lines.append(f"| {e.name} | {e.event_count or 0:,} | {e.visit_count or 0:,} |")

            (out_dir / f"site-{site_id}.md").write_text("\n".join(lines) + "\n")
            count += 1

    if count:
        logger.info(f"Generated {count} matomo cache files")
    else:
        logger.info("No matomo baselines in DB, skipping")


def warmup_metabase_cards():
    with get_db() as session:
        instance_names = session.scalars(select(MetabaseCard.instance).distinct()).all()

    if not instance_names:
        logger.info("No metabase cards in DB, skipping")
        return

    for instance in instance_names:
        out_dir = CACHE_DIR / "metabase" / instance
        cards_dir = out_dir / "cards"
        dashboards_dir = out_dir / "dashboards"
        cards_dir.mkdir(parents=True, exist_ok=True)
        dashboards_dir.mkdir(parents=True, exist_ok=True)

        with get_db() as session:
            topics = session.execute(
                select(MetabaseCard.topic, func.count())
                .where(MetabaseCard.instance == instance)
                .group_by(MetabaseCard.topic)
                .order_by(func.count().desc())
            ).all()

            for topic, _ in topics:
                cards = session.scalars(
                    select(MetabaseCard)
                    .where(MetabaseCard.instance == instance, MetabaseCard.topic == topic)
                    .order_by(MetabaseCard.id)
                ).all()

                lines = [f"# {topic}", "", f"**{len(cards)} cartes**", ""]
                for c in cards:
                    lines.append(f"## [{c.id}] {c.name}")
                    if c.description:
                        lines.append(f"\n{c.description}")
                    if c.dashboard_name:
                        lines.append(f"\n*Dashboard: {c.dashboard_name}*")
                    if c.sql_query:
                        sql = c.sql_query[:2000]
                        lines.append(f"\n```sql\n{sql}\n```")
                    lines.append("")

                (cards_dir / f"topic-{topic}.md").write_text("\n".join(lines) + "\n")

            dashboards = session.scalars(
                select(MetabaseDashboard).where(MetabaseDashboard.instance == instance).order_by(MetabaseDashboard.id)
            ).all()

            for dash in dashboards:
                cards = session.scalars(
                    select(MetabaseCard)
                    .where(MetabaseCard.instance == instance, MetabaseCard.dashboard_id == dash.id)
                    .order_by(MetabaseCard.id)
                ).all()
                lines = [f"# Dashboard {dash.id}: {dash.name}", ""]
                if dash.pilotage_url:
                    lines.append(f"URL: {dash.pilotage_url}")
                lines.append(f"\n**{len(cards)} cartes**\n")
                for c in cards:
                    sql_preview = (c.sql_query or "")[:200].replace("\n", " ")
                    lines.append(f"- [{c.id}] {c.name} ({c.topic or '?'}) — `{sql_preview}`")
                lines.append("")
                (dashboards_dir / f"dashboard-{dash.id}.md").write_text("\n".join(lines) + "\n")

        logger.info(
            f"Generated metabase cache for instance '{instance}': {len(topics)} topics, {len(dashboards)} dashboards"
        )


def restore_interactive_from_s3():
    if not config.S3_BUCKET:
        logger.info("S3 not configured, skipping restore")
        return

    from . import s3 as s3_module

    files = s3_module.list_files()
    restored = 0
    for f in files:
        rel_path = f["path"]
        local_path = config.INTERACTIVE_DIR / rel_path
        if local_path.exists():
            continue
        content = s3_module.download_file(rel_path)
        if content is not None:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(content)
            restored += 1

    if restored:
        logger.info(f"Restored {restored} interactive files from S3")


def run():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    config.INTERACTIVE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Warming up cache in {CACHE_DIR}")

    for attempt in range(3):
        try:
            init_db()
            break
        except Exception:
            if attempt == 2:
                logger.exception("Warmup failed after 3 attempts: cannot connect to database")
                return
            logger.warning(f"Database unavailable (attempt {attempt + 1}/3), retrying in 5s...")
            time.sleep(5)

    warmup_matomo_baselines()
    warmup_metabase_cards()
    restore_interactive_from_s3()
    cache_files = list(CACHE_DIR.rglob("*.md"))
    logger.info(f"Warmup complete — {len(cache_files)} cache files in {CACHE_DIR}")


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    run()
