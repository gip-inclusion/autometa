"""APP.md frontmatter parser (legacy — kept for the import migration)."""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


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
