"""dashboards import — populate dashboards/dashboard_tags from APP.md files."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence, Union

from sqlalchemy import text

from alembic import op
from lib.dashboards import detect_api_flags, normalize_tag_name
from web import config
from web import s3 as s3_module
from web.dashboards import parse_app_md

revision: str = "d37119f978f5"
down_revision: Union[str, Sequence[str], None] = "7946c9c555a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration.dashboards_import")

# Why: one-shot rules for the V1 import only. Cleans legacy tagging where dashboards were
# called "appli" and where naming drifted (contact/contacts, multi/cross-produit/multi-produits…).
# Lives here, not in lib/, because runtime code shouldn't carry historical baggage.
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


def upgrade() -> None:
    interactive_dir = config.INTERACTIVE_DIR

    local_app_mds = sorted(interactive_dir.glob("*/APP.md")) if interactive_dir.exists() else []
    if not local_app_mds and config.S3_BUCKET:
        _hydrate_from_s3(interactive_dir)
        local_app_mds = sorted(interactive_dir.glob("*/APP.md"))

    if not local_app_mds:
        logger.info("No APP.md to import (local empty, no S3 fallback). Skipping.")
        return

    bind = op.get_bind()
    imported = 0
    skipped = 0

    for app_md in local_app_mds:
        slug_dir = app_md.parent
        slug = slug_dir.name
        try:
            content = app_md.read_text()
        except OSError as exc:
            logger.warning("Cannot read %s: %s", app_md, exc)
            skipped += 1
            continue

        meta = parse_app_md(content, slug)
        if meta is None:
            logger.warning("Skipping %s: invalid frontmatter", app_md)
            skipped += 1
            continue

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
        conversation_id = meta["conversation_id"] or None

        if meta["updated"] is not None:
            created_at = meta["updated"]
        else:
            try:
                created_at = datetime.fromtimestamp(app_md.stat().st_mtime, tz=timezone.utc)
            except OSError:
                created_at = datetime.now(timezone.utc)

        bind.execute(
            text("""
                INSERT INTO dashboards (
                    slug, title, description, website, category,
                    first_author_email, created_in_conversation_id,
                    is_archived, has_api_access, has_cron, has_persistence,
                    created_at, updated_at
                ) VALUES (
                    :slug, :title, :description, :website, :category,
                    :first_author_email, :created_in_conversation_id,
                    false, :has_api_access, :has_cron, :has_persistence,
                    :created_at, :updated_at
                )
                ON CONFLICT (slug) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    website = EXCLUDED.website,
                    category = EXCLUDED.category,
                    first_author_email = EXCLUDED.first_author_email,
                    created_in_conversation_id = EXCLUDED.created_in_conversation_id,
                    has_api_access = EXCLUDED.has_api_access,
                    has_cron = EXCLUDED.has_cron,
                    has_persistence = EXCLUDED.has_persistence,
                    updated_at = EXCLUDED.updated_at
            """),
            {
                "slug": slug,
                "title": meta["title"],
                "description": meta["description"] or None,
                "website": meta["website"] or None,
                "category": meta["category"] or None,
                "first_author_email": first_author,
                "created_in_conversation_id": conversation_id,
                "has_api_access": has_api_access,
                "has_cron": has_cron,
                "has_persistence": has_persistence,
                "created_at": created_at,
                "updated_at": created_at,
            },
        )

        canonical_tags: list[str] = []
        for raw in meta["tags"]:
            canonical = _v1_canonical_tag(raw)
            if canonical is not None and canonical not in canonical_tags:
                canonical_tags.append(canonical)
        for tag_name in canonical_tags:
            bind.execute(
                text(
                    "INSERT INTO tags (name, type, label) VALUES (:name, 'dashboard', :name) "
                    "ON CONFLICT (name) DO NOTHING"
                ),
                {"name": tag_name},
            )
            tag_id = bind.execute(
                text("SELECT id FROM tags WHERE name = :name"),
                {"name": tag_name},
            ).scalar()
            bind.execute(
                text(
                    "INSERT INTO dashboard_tags (dashboard_slug, tag_id) VALUES (:slug, :tag_id) ON CONFLICT DO NOTHING"
                ),
                {"slug": slug, "tag_id": tag_id},
            )

        imported += 1

    logger.info("dashboards import: imported=%d skipped=%d", imported, skipped)


def downgrade() -> None:
    op.execute(text("DELETE FROM dashboard_tags"))
    op.execute(text("DELETE FROM dashboards"))
