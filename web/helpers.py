"""Shared helper functions for the web application."""

import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config
from .config import DISPLAY_TIMEZONE

DISPLAY_TZ = ZoneInfo(DISPLAY_TIMEZONE)
_DAY_NAMES = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")


def utcnow():
    return datetime.now(timezone.utc)


def now_local():
    return datetime.now(DISPLAY_TZ)


def sanitize_for_log(value: str) -> str:
    """Strip CR/LF from user-controlled values before logging (log-injection guard)."""
    return value.replace("\r", "").replace("\n", "")


def to_local(dt):
    return dt.astimezone(DISPLAY_TZ)


def format_relative_date(dt):
    now = now_local()
    dt = to_local(dt)
    today = now.date()
    dt_date = dt.date()

    days_since_monday = today.weekday()
    this_week_start = today - timedelta(days=days_since_monday)

    if dt_date == today:
        return dt.strftime("%H:%M")
    elif dt_date == today - timedelta(days=1):
        return f"hier, {dt.strftime('%H:%M')}"
    elif this_week_start <= dt_date < today:
        return f"{_DAY_NAMES[dt_date.weekday()]} {dt.strftime('%H:%M')}"
    else:
        return dt.strftime("%d/%m/%Y à %H:%M")


def format_future_date(dt):
    """Friendly future timestamp: 'demain à 06:00', 'lundi à 06:00', 'le 12/06 à 06:00'."""
    now = now_local()
    dt = to_local(dt)
    today = now.date()
    dt_date = dt.date()
    if dt_date == today:
        return f"aujourd'hui à {dt.strftime('%H:%M')}"
    if dt_date == today + timedelta(days=1):
        return f"demain à {dt.strftime('%H:%M')}"
    if dt_date < today + timedelta(days=7):
        return f"{_DAY_NAMES[dt_date.weekday()]} à {dt.strftime('%H:%M')}"
    return dt.strftime("le %d/%m à %H:%M")


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
    if not re.match(r"^[a-zA-Z0-9_\-./]+\.md$", file_param):
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


def validate_conv_id(conv_id: str) -> bool:
    try:
        uuid.UUID(conv_id)
        return True
    except ValueError, AttributeError:
        return False


def get_staging_dir(conv_id: str) -> Path:
    if not validate_conv_id(conv_id):
        raise ValueError("Invalid conversation ID")
    return KNOWLEDGE_DRAFTS_ROOT / conv_id


def list_staged_files(conv_id: str) -> list[str]:
    if not validate_conv_id(conv_id):
        return []
    staging_dir = get_staging_dir(conv_id)
    if not staging_dir.exists():
        return []

    files = []
    for f in staging_dir.rglob("*.md"):
        try:
            rel_path = f.relative_to(staging_dir)
            files.append(str(rel_path))
        except ValueError:
            continue
    return sorted(files)


def list_knowledge_files() -> dict[str, list[dict]]:
    sections = {}

    for f in sorted(KNOWLEDGE_ROOT.rglob("*.md")):
        rel_path = f.relative_to(KNOWLEDGE_ROOT)
        # Why: tester le chemin absolu masquait tout le dossier quand le dépôt vit sous un répertoire caché (worktree).
        if any(part.startswith(".") for part in rel_path.parts):
            continue

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
