"""Dashboard inventory and lifecycle helpers."""

import logging
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from web import config
from web.db import get_db
from web.models import Dashboard, DashboardTag, Tag

logger = logging.getLogger(__name__)

_STAGING_PREFIX = ".tmp-"

_WRITE_SQL_RE = re.compile(
    r"\b("
    r"INSERT\s+INTO"
    r"|UPDATE\s+\w+\s+SET"
    r"|DELETE\s+FROM"
    r"|CREATE\s+(TABLE|INDEX|VIEW|UNIQUE\s+INDEX)"
    r"|ALTER\s+TABLE"
    r"|DROP\s+(TABLE|INDEX|VIEW)"
    r")\b",
    re.IGNORECASE,
)

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def normalize_tag_name(raw: str) -> str | None:
    """Lowercase + kebab-case + strip. Retourne None si vide."""
    name = raw.strip().lower().replace(" ", "-")
    return name or None


def normalize_tags(raw_tags: list[str]) -> list[str]:
    return list(dict.fromkeys(t for t in (normalize_tag_name(r) for r in raw_tags) if t is not None))


class DashboardNotFound(Exception):
    """Raised when a slug doesn't resolve to an existing dashboard row."""


@dataclass
class DashboardUpdateResult:
    slug: str
    originating_user_email: str
    updater_email: str
    fields_changed: list[str]


def detect_api_flags(slug_dir: Path, metadata: dict) -> tuple[bool, bool]:
    """Retourne (has_api_access, has_persistence) — frontmatter prime, sinon heuristique V0."""
    api = metadata.get("has_api_access")
    persist = metadata.get("has_persistence")
    if api is not None and persist is not None:
        return bool(api), bool(persist)

    code_parts: list[str] = []
    for pattern in ("*.js", "*.html"):
        for path in slug_dir.rglob(pattern):
            code_parts.append(path.read_text(errors="replace"))
    code = "\n".join(code_parts)

    detected_api = "/api/query" in code
    # Why: has_persistence (écriture datalake) passe par /api/query — sans appel /api/query,
    # un verbe SQL d'écriture dans le code n'a pas d'effet persistant.
    detected_persist = detected_api and bool(_WRITE_SQL_RE.search(code))

    return (
        bool(api) if api is not None else detected_api,
        bool(persist) if persist is not None else detected_persist,
    )


def create_dashboard(
    *,
    slug: str,
    title: str,
    description: str | None,
    website: str | None,
    category: str | None,
    tags: list[str],
    has_cron: bool = False,
    has_api_access: bool = False,
    has_persistence: bool = False,
    first_author_email: str,
    created_in_conversation_id: str | None,
) -> Dashboard:
    """Crée un TDB : insertion DB + scaffold du dossier `data/interactive/{slug}/`."""
    if not _SLUG_RE.match(slug) or not 1 <= len(slug) <= 100:
        raise ValueError(f"Invalid slug: {slug!r}")

    final_dir = config.INTERACTIVE_DIR / slug
    template_dir = config.BASE_DIR / "docs" / "dashboard-template"

    if final_dir.exists():
        raise ValueError(f"Slug already exists on disk: {final_dir}")

    # Why: scaffold staged sur le même FS pour un rename atomique avant le commit DB.
    # En cas de SIGKILL entre rename et commit, on tolère un dossier orphelin (GC par
    # cleanup_orphan_scaffolds), jamais l'inverse (ligne DB sans scaffold = app cassée).
    staging_dir = config.INTERACTIVE_DIR / f"{_STAGING_PREFIX}{slug}-{uuid.uuid4().hex}"
    staging_dir.mkdir(parents=True)
    renamed = False
    try:
        for src in template_dir.iterdir():
            if src.name == "APP.md":
                continue
            if src.name == "cron.py" and not has_cron:
                continue
            shutil.copy2(src, staging_dir / src.name)

        (staging_dir / "APP.md").write_text(
            _render_app_md(
                title=title,
                description=description,
                website=website,
                category=category,
                tags=tags,
                first_author_email=first_author_email,
                conversation_id=created_in_conversation_id,
                has_cron=has_cron,
                has_api_access=has_api_access,
                has_persistence=has_persistence,
            )
        )

        with get_db() as session:
            if session.scalar(select(Dashboard).where(Dashboard.slug == slug)) is not None:
                raise ValueError(f"Slug already exists in DB: {slug}")

            now = datetime.now(timezone.utc)
            dashboard = Dashboard(
                slug=slug,
                title=title,
                description=description,
                website=website,
                category=category,
                first_author_email=first_author_email,
                created_in_conversation_id=created_in_conversation_id,
                is_archived=False,
                has_api_access=has_api_access,
                has_cron=has_cron,
                has_persistence=has_persistence,
                created_at=now,
                updated_at=now,
            )
            session.add(dashboard)
            session.flush()

            for tag_name in normalize_tags(tags):
                tag = _upsert_tag(session, tag_name)
                session.add(DashboardTag(dashboard_slug=slug, tag_id=tag.id))

            session.flush()
            os.rename(staging_dir, final_dir)
            renamed = True
            session.refresh(dashboard)
            session.expunge(dashboard)
            return dashboard
    except Exception:
        shutil.rmtree(final_dir if renamed else staging_dir, ignore_errors=True)
        raise


def cleanup_orphan_scaffolds(staging_max_age_minutes: int = 10) -> dict:
    """GC : supprime les stagings expirés et les dossiers slug sans ligne DB."""
    if not config.INTERACTIVE_DIR.exists():
        return {"removed_staging": [], "removed_orphan": []}

    now_ts = datetime.now(timezone.utc).timestamp()
    removed_staging: list[str] = []
    removed_orphan: list[str] = []

    with get_db() as session:
        known = set(session.scalars(select(Dashboard.slug)).all())

    for path in config.INTERACTIVE_DIR.iterdir():
        if not path.is_dir():
            continue
        if path.name.startswith(_STAGING_PREFIX):
            age_min = (now_ts - path.stat().st_mtime) / 60
            if age_min > staging_max_age_minutes:
                shutil.rmtree(path, ignore_errors=True)
                removed_staging.append(path.name)
            continue
        if path.name not in known:
            shutil.rmtree(path, ignore_errors=True)
            removed_orphan.append(path.name)

    if removed_staging or removed_orphan:
        logger.warning(
            "orphan scaffolds cleaned: staging=%s orphan=%s",
            removed_staging,
            removed_orphan,
        )
    return {"removed_staging": removed_staging, "removed_orphan": removed_orphan}


def main() -> None:
    """CLI: nettoyage périodique des scaffolds orphelins."""
    logging.basicConfig(level=logging.INFO)
    result = cleanup_orphan_scaffolds()
    logger.info(
        "cleanup-dashboards: removed_staging=%d removed_orphan=%d",
        len(result["removed_staging"]),
        len(result["removed_orphan"]),
    )


def _upsert_tag(session: Session, name: str) -> Tag:
    tag = session.scalar(select(Tag).where(Tag.name == name))
    if tag is not None:
        return tag
    tag = Tag(name=name, type="dashboard", label=name)
    session.add(tag)
    session.flush()
    return tag


# TODO(louije/dashboard-drop-app-md): supprimer ce bloc et tout l'écosystème APP.md
# (_render_app_md, _extract_app_md_body, _sync_app_md) une fois cron_schedule/cron_timeout
# ajoutés à la table `dashboards` et `web/cron.py` migré sur la DB. Cf. spec V1 §5.
def _frontmatter_lines(
    *,
    title: str,
    description: str | None,
    website: str | None,
    category: str | None,
    tags: list[str],
    first_author_email: str,
    conversation_id: str | None,
    has_cron: bool,
    has_api_access: bool,
    has_persistence: bool,
) -> list[str]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    description_clean = (description or "").replace("\n", " ").strip()
    return [
        f"title: {title}",
        f"description: {description_clean}",
        f"updated: {today}",
        f"website: {website or ''}",
        f"category: {category or ''}",
        f"tags: {', '.join(tags)}",
        f"authors: {first_author_email}",
        f"conversation_id: {conversation_id or ''}",
        "",
        f"cron: {'true' if has_cron else 'false'}",
        f"has_api_access: {'true' if has_api_access else 'false'}",
        f"has_persistence: {'true' if has_persistence else 'false'}",
    ]


def _render_app_md(
    *,
    title: str,
    description: str | None,
    website: str | None,
    category: str | None,
    tags: list[str],
    first_author_email: str,
    conversation_id: str | None,
    has_cron: bool,
    has_api_access: bool,
    has_persistence: bool,
) -> str:
    description_clean = (description or "").replace("\n", " ").strip()
    fm = "\n".join(
        _frontmatter_lines(
            title=title,
            description=description,
            website=website,
            category=category,
            tags=tags,
            first_author_email=first_author_email,
            conversation_id=conversation_id,
            has_cron=has_cron,
            has_api_access=has_api_access,
            has_persistence=has_persistence,
        )
    )
    body = description_clean or "TODO"
    return f"---\n{fm}\n---\n\n## À propos\n\n{body}\n"


def _extract_app_md_body(text: str) -> str:
    """Returns `---<body-after-closing>` from APP.md text. Falls back to `---\\n` if malformed."""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "---\n"
    return "---" + parts[2]


def _apply_tag_updates(
    session: Session,
    slug: str,
    add_tags: list[str] | None,
    remove_tags: list[str] | None,
    set_tags: list[str] | None,
) -> bool:
    if set_tags is None and not add_tags and not remove_tags:
        return False

    current = session.execute(
        select(Tag.name, Tag.id)
        .join(DashboardTag, DashboardTag.tag_id == Tag.id)
        .where(DashboardTag.dashboard_slug == slug)
    ).all()
    current_names = {row[0] for row in current}

    if set_tags is not None:
        target = set(normalize_tags(set_tags))
    else:
        target = (current_names | set(normalize_tags(add_tags or []))) - set(normalize_tags(remove_tags or []))

    if target == current_names:
        return False

    to_remove_ids = [row[1] for row in current if row[0] in (current_names - target)]
    if to_remove_ids:
        session.execute(
            delete(DashboardTag)
            .where(DashboardTag.dashboard_slug == slug)
            .where(DashboardTag.tag_id.in_(to_remove_ids))
        )

    for name in target - current_names:
        tag = _upsert_tag(session, name)
        session.add(DashboardTag(dashboard_slug=slug, tag_id=tag.id))

    return True


def _sync_app_md(session: Session, dashboard: Dashboard) -> None:
    app_md_path = config.INTERACTIVE_DIR / dashboard.slug / "APP.md"
    if not app_md_path.exists():
        logger.warning("APP.md missing for slug %s, skipping sync", dashboard.slug)
        return

    tag_names = list(
        session.scalars(
            select(Tag.name)
            .join(DashboardTag, DashboardTag.tag_id == Tag.id)
            .where(DashboardTag.dashboard_slug == dashboard.slug)
        ).all()
    )
    fm = "\n".join(
        _frontmatter_lines(
            title=dashboard.title,
            description=dashboard.description,
            website=dashboard.website,
            category=dashboard.category,
            tags=tag_names,
            first_author_email=dashboard.first_author_email,
            conversation_id=dashboard.created_in_conversation_id,
            has_cron=dashboard.has_cron,
            has_api_access=dashboard.has_api_access,
            has_persistence=dashboard.has_persistence,
        )
    )
    body = _extract_app_md_body(app_md_path.read_text())
    app_md_path.write_text(f"---\n{fm}\n{body}")


def update_dashboard(
    *,
    slug: str,
    updater_email: str,
    in_conversation_id: str,
    title: str | None = None,
    description: str | None = None,
    website: str | None = None,
    category: str | None = None,
    add_tags: list[str] | None = None,
    remove_tags: list[str] | None = None,
    set_tags: list[str] | None = None,
    has_cron: bool | None = None,
    has_api_access: bool | None = None,
    has_persistence: bool | None = None,
    is_archived: bool | None = None,
) -> DashboardUpdateResult:
    """Met à jour les métadonnées d'un TDB existant (DB + sync APP.md). None = no change."""
    if set_tags is not None and (add_tags or remove_tags):
        raise ValueError("set_tags is mutually exclusive with add_tags/remove_tags")

    fields_changed: list[str] = []
    syncable_changed = False

    with get_db() as session:
        dashboard = session.scalar(select(Dashboard).where(Dashboard.slug == slug))
        if dashboard is None:
            raise DashboardNotFound(slug)
        originating = dashboard.first_author_email

        scalar_updates = {
            "title": title,
            "description": description,
            "website": website,
            "category": category,
            "has_cron": has_cron,
            "has_api_access": has_api_access,
            "has_persistence": has_persistence,
            "is_archived": is_archived,
        }
        for field_name, value in scalar_updates.items():
            if value is None:
                continue
            if getattr(dashboard, field_name) != value:
                setattr(dashboard, field_name, value)
                fields_changed.append(field_name)
                if field_name != "is_archived":
                    syncable_changed = True

        if _apply_tag_updates(session, slug, add_tags, remove_tags, set_tags):
            fields_changed.append("tags")
            syncable_changed = True

        if fields_changed:
            dashboard.updated_at = datetime.now(timezone.utc)
            if syncable_changed:
                _sync_app_md(session, dashboard)

        logger.info(
            "update_dashboard slug=%s updater=%s conv=%s originating=%s changed=%s",
            slug,
            updater_email,
            in_conversation_id,
            originating,
            fields_changed,
        )

        return DashboardUpdateResult(
            slug=slug,
            originating_user_email=originating,
            updater_email=updater_email,
            fields_changed=fields_changed,
        )
