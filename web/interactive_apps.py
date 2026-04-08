"""Scan and cache interactive apps under data/interactive (S3 or local)."""

import logging
from datetime import datetime, timezone

from . import s3

logger = logging.getLogger(__name__)

apps_cache: list[dict] | None = None


def parse_app_md(content: str, folder_name: str) -> dict | None:
    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    fm = {}
    for line in parts[1].strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            fm[key.strip().lower()] = value.strip()

    if "title" not in fm:
        return None

    updated = None
    if "updated" in fm:
        try:
            updated = datetime.strptime(fm["updated"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            logger.debug("Invalid date format in APP.md: %s", fm["updated"])

    tags = []
    if "tags" in fm:
        raw_tags = fm["tags"]
        if raw_tags.startswith("[") and raw_tags.endswith("]"):
            tags = [t.strip() for t in raw_tags[1:-1].split(",") if t.strip()]
        else:
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]

    authors = []
    if "authors" in fm:
        authors = [a.strip() for a in fm["authors"].split(",") if a.strip()]

    return {
        "slug": folder_name,
        "title": fm.get("title"),
        "description": fm.get("description", ""),
        "website": fm.get("website"),
        "category": fm.get("category"),
        "tags": tags,
        "authors": authors,
        "conversation_id": fm.get("conversation_id"),
        "updated": updated,
        "url": f"/interactive/{folder_name}/",
        "is_interactive": True,
    }


def invalidate_apps_cache():
    global apps_cache
    apps_cache = None


def scan_interactive_apps():
    """
    Scan /data/interactive/ for valid apps (S3 or local filesystem).

    An app is valid if it has an APP.md file with YAML front-matter.
    Returns list of dicts matching report structure where possible.

    Results are cached and invalidated on write (when sync_to_s3 uploads
    an APP.md file).
    """
    global apps_cache

    if apps_cache is not None:
        return apps_cache

    apps = scan_interactive_apps_uncached()
    apps_cache = apps
    return apps


def scan_interactive_apps_uncached():
    apps = []
    for folder_name in s3.interactive.list_directories():
        app_md_content = s3.interactive.download(f"{folder_name}/APP.md")
        if app_md_content:
            try:
                content = app_md_content.decode("utf-8")
                app = parse_app_md(content, folder_name)
                if app:
                    apps.append(app)
            except UnicodeDecodeError:
                continue

    dated = [a for a in apps if a["updated"] is not None]
    undated = [a for a in apps if a["updated"] is None]
    dated.sort(key=lambda a: (a["updated"], a["title"]), reverse=True)
    undated.sort(key=lambda a: a["title"])
    apps[:] = dated + undated
    return apps
