"""One-shot V1 importer: APP.md files → dashboards/dashboard_tags.

Run once after the V1 schema migration is applied:

    python -m lib.dashboards_import_v1

Idempotent: re-running upserts existing rows. Reads APP.md from
INTERACTIVE_DIR; falls back to S3 hydration when the local dir is empty.

Why a script and not a migration: the operation depends on filesystem and
S3 state, so it is not reproducible on a fresh DB (CI, new env). It is also
V1-specific historical baggage — once executed in prod, this file and its
test can be deleted.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from lib.dashboards import detect_api_flags, normalize_tag_name
from web import config
from web import s3 as s3_module
from web.db import get_db
from web.models import Dashboard, DashboardTag, Tag

logger = logging.getLogger(__name__)

_V1_TAG_BLOCKLIST = {"appli", "dashboard", "dev", "metabase"}
_V1_TAG_ALIASES = {
    "contact": "contacts",
    "orientations": "orientation",
    "rétention": "retention",
    "cross-produit": "multi-produits",
    "multi": "multi-produits",
}


def _v1_canonical_tag(raw: str) -> str | None:
    name = normalize_tag_name(raw)
    if name is None or name in _V1_TAG_BLOCKLIST:
        return None
    return _V1_TAG_ALIASES.get(name, name)


def _parse_raw_fm(content: str) -> dict[str, str]:
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    fm: dict[str, str] = {}
    for line in parts[1].strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            fm[key.strip().lower()] = value.strip()
    return fm


def _to_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return value.strip().lower() not in ("false", "no", "0", "off", "")


def _parse_app_md(content: str, slug: str) -> dict | None:
    fm = _parse_raw_fm(content)
    if "title" not in fm:
        return None

    updated = None
    if "updated" in fm:
        try:
            updated = datetime.strptime(fm["updated"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            logger.debug("Invalid date format in APP.md for %s: %s", slug, fm["updated"])

    raw_tags = fm.get("tags", "")
    if raw_tags.startswith("[") and raw_tags.endswith("]"):
        raw_tags = raw_tags[1:-1]
    tags = [t.strip() for t in raw_tags.split(",") if t.strip()]

    authors = [a.strip() for a in fm.get("authors", "").split(",") if a.strip()]

    return {
        "slug": slug,
        "title": fm["title"],
        "description": fm.get("description") or None,
        "website": fm.get("website") or None,
        "category": fm.get("category") or None,
        "tags": tags,
        "authors": authors,
        "conversation_id": fm.get("conversation_id") or None,
        "updated": updated,
    }


def _hydrate_from_s3(interactive_dir: Path) -> int:
    interactive_dir.mkdir(parents=True, exist_ok=True)
    slugs = s3_module.interactive.list_directories()
    downloaded = 0
    for slug in slugs:
        for f in s3_module.interactive.list_files(slug):
            path = f["path"]
            content = s3_module.interactive.download(path)
            if content is None:
                continue
            local_path = interactive_dir / path
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(content)
            downloaded += 1
    logger.info("Hydrated %d slug(s) (%d files) from S3 to %s", len(slugs), downloaded, interactive_dir)
    return len(slugs)


def _upsert_tag(session: Session, name: str) -> Tag:
    tag = session.scalar(select(Tag).where(Tag.name == name))
    if tag is not None:
        return tag
    tag = Tag(name=name, type="dashboard", label=name)
    session.add(tag)
    session.flush()
    return tag


def _import_one(session: Session, app_md: Path) -> bool:
    slug_dir = app_md.parent
    slug = slug_dir.name

    try:
        content = app_md.read_text()
    except OSError as exc:
        logger.warning("Cannot read %s: %s", app_md, exc)
        return False

    meta = _parse_app_md(content, slug)
    if meta is None:
        logger.warning("Skipping %s: invalid frontmatter", app_md)
        return False

    raw_fm = _parse_raw_fm(content)

    fm_for_heuristic: dict[str, bool] = {}
    api_explicit = _to_bool(raw_fm.get("has_api_access"))
    if api_explicit is not None:
        fm_for_heuristic["has_api_access"] = api_explicit
    persist_explicit = _to_bool(raw_fm.get("has_persistence"))
    if persist_explicit is not None:
        fm_for_heuristic["has_persistence"] = persist_explicit
    has_api_access, has_persistence = detect_api_flags(slug_dir, fm_for_heuristic)

    cron_explicit = _to_bool(raw_fm.get("cron"))
    has_cron = True if cron_explicit is None else cron_explicit

    first_author = meta["authors"][0] if meta["authors"] else "unknown@autometa"

    if meta["updated"] is not None:
        created_at = meta["updated"]
    else:
        try:
            created_at = datetime.fromtimestamp(app_md.stat().st_mtime, tz=timezone.utc)
        except OSError:
            created_at = datetime.now(timezone.utc)

    dashboard = session.scalar(select(Dashboard).where(Dashboard.slug == slug))
    if dashboard is None:
        dashboard = Dashboard(
            slug=slug,
            title=meta["title"],
            description=meta["description"],
            website=meta["website"],
            category=meta["category"],
            first_author_email=first_author,
            created_in_conversation_id=meta["conversation_id"],
            is_archived=False,
            has_api_access=has_api_access,
            has_cron=has_cron,
            has_persistence=has_persistence,
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(dashboard)
    else:
        dashboard.title = meta["title"]
        dashboard.description = meta["description"]
        dashboard.website = meta["website"]
        dashboard.category = meta["category"]
        dashboard.first_author_email = first_author
        dashboard.created_in_conversation_id = meta["conversation_id"]
        dashboard.has_api_access = has_api_access
        dashboard.has_cron = has_cron
        dashboard.has_persistence = has_persistence
        dashboard.updated_at = created_at

    session.flush()

    canonical_tags: list[str] = []
    for raw in meta["tags"]:
        canonical = _v1_canonical_tag(raw)
        if canonical is not None and canonical not in canonical_tags:
            canonical_tags.append(canonical)

    for tag_name in canonical_tags:
        tag = _upsert_tag(session, tag_name)
        existing = session.scalar(
            select(DashboardTag).where(
                DashboardTag.dashboard_slug == slug,
                DashboardTag.tag_id == tag.id,
            )
        )
        if existing is None:
            session.add(DashboardTag(dashboard_slug=slug, tag_id=tag.id))

    return True


def run_import() -> dict[str, int]:
    interactive_dir = config.INTERACTIVE_DIR

    local_app_mds = sorted(interactive_dir.glob("*/APP.md")) if interactive_dir.exists() else []
    if not local_app_mds and config.S3_BUCKET:
        _hydrate_from_s3(interactive_dir)
        local_app_mds = sorted(interactive_dir.glob("*/APP.md"))

    if not local_app_mds:
        logger.info("No APP.md to import (local empty, no S3 fallback). Skipping.")
        return {"imported": 0, "skipped": 0}

    imported = 0
    skipped = 0
    with get_db() as session:
        for app_md in local_app_mds:
            if _import_one(session, app_md):
                imported += 1
            else:
                skipped += 1

    logger.info("dashboards import: imported=%d skipped=%d", imported, skipped)
    return {"imported": imported, "skipped": skipped}


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_import()


if __name__ == "__main__":
    main()
