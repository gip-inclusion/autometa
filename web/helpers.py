"""Shared helper functions for the web application."""

import re
from pathlib import Path

from . import config

# Knowledge path constants
KNOWLEDGE_ROOT = (config.BASE_DIR / "knowledge").resolve()
KNOWLEDGE_DRAFTS_ROOT = config.BASE_DIR / "data" / "knowledge-drafts"
ALLOWED_EXTENSIONS = {".md"}


def validate_knowledge_path(file_param: str) -> Path | None:
    """
    Validate and resolve a knowledge file path.
    Returns None if invalid/unsafe.
    """
    if not file_param:
        return None

    # Reject obvious attacks early
    if ".." in file_param or file_param.startswith("/"):
        return None

    # Only allow simple alphanumeric + hyphen/underscore/dot + slash
    if not re.match(r'^[a-zA-Z0-9_\-./]+\.md$', file_param):
        return None

    # No double slashes, no hidden files
    if "//" in file_param or "/." in file_param:
        return None

    # Resolve full path
    candidate = (KNOWLEDGE_ROOT / file_param).resolve()

    # CRITICAL: ensure it's inside knowledge/
    try:
        candidate.relative_to(KNOWLEDGE_ROOT)
    except ValueError:
        return None  # Path escapes knowledge/

    # Must exist and be a file
    if not candidate.is_file():
        return None

    # Extension check (belt + suspenders)
    if candidate.suffix.lower() not in ALLOWED_EXTENSIONS:
        return None

    return candidate


def get_staging_dir(conv_id: str) -> Path:
    """Get staging directory for a knowledge conversation."""
    return KNOWLEDGE_DRAFTS_ROOT / conv_id


def list_staged_files(conv_id: str) -> list[str]:
    """List files in staging directory relative to knowledge root."""
    staging_dir = get_staging_dir(conv_id)
    if not staging_dir.exists():
        return []

    files = []
    for f in staging_dir.rglob("*.md"):
        try:
            rel_path = f.relative_to(staging_dir)
            files.append(str(rel_path))
        except ValueError:
            pass
    return sorted(files)


def list_knowledge_files() -> dict[str, list[dict]]:
    """List all knowledge files grouped by subfolder."""
    sections = {}

    for f in sorted(KNOWLEDGE_ROOT.rglob("*.md")):
        if any(part.startswith(".") for part in f.parts):
            continue

        rel_path = f.relative_to(KNOWLEDGE_ROOT)
        # Section is the parent directory path (e.g., "stats", "stats/cards")
        # Use "." for root-level files
        section = str(rel_path.parent) if rel_path.parent != Path(".") else "."

        # Humanize the name
        name = f.stem
        name = re.sub(r"^\d{4}-\d{2}(-\d{2})?[-_]?", "", name)
        name = re.sub(r"[-_]+", " ", name)
        if name:
            name = name[0].upper() + name[1:]

        if section not in sections:
            sections[section] = []

        sections[section].append({
            "path": str(rel_path),
            "name": name,
            "modified": f.stat().st_mtime,
        })

    # Sort sections by name, with top-level folders first
    return dict(sorted(sections.items(), key=lambda x: (x[0].count("/"), x[0])))
