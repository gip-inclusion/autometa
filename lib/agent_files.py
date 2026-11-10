"""An agent's own files, kept by Autometa in Postgres and versioned: never sent outside, written only if declared."""

import difflib
import logging
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lib.agent_config import AGENT_FILE_MAX
from web.models import AgentFileVersion

logger = logging.getLogger(__name__)

__all__ = ["read", "history", "compare", "write_version", "with_entries", "output_errors"]

ENTRY = re.compile(r"(?m)^<!-- entree: ([0-9a-z-]+) -->\n")


def history(session: Session, agent_id: int, name: str) -> list[dict]:
    """Every version of a file, oldest first: number, date, origin, size; never the content."""
    rows = session.execute(
        select(
            AgentFileVersion.version,
            AgentFileVersion.created_at,
            AgentFileVersion.origin,
            func.length(AgentFileVersion.content),
        )
        .where(AgentFileVersion.agent_id == agent_id, AgentFileVersion.name == name)
        .order_by(AgentFileVersion.version)
    )
    return [
        {"version": v, "written_at": at.isoformat(timespec="seconds"), "origin": origin, "size": size}
        for v, at, origin, size in rows
    ]


def read(session: Session, agent_id: int, name: str, version: int | None = None) -> dict:
    """A version of a file, the latest by default; version 0 is the empty file before any write."""
    latest = latest_version(session, agent_id, name)
    number = latest if version is None else version
    if not 0 <= number <= latest:
        raise ValueError(f"fichier {name} : version {number} inconnue, versions 1 à {latest}")
    if number == 0:
        return {"name": name, "version": 0, "content": ""}
    row = session.scalar(
        select(AgentFileVersion).where(
            AgentFileVersion.agent_id == agent_id, AgentFileVersion.name == name, AgentFileVersion.version == number
        )
    )
    return {
        "name": name,
        "version": number,
        "written_at": row.created_at.isoformat(timespec="seconds"),
        "origin": row.origin,
        "size": len(row.content),
        "content": row.content,
    }


def latest_version(session: Session, agent_id: int, name: str) -> int:
    found = session.scalar(
        select(func.max(AgentFileVersion.version)).where(
            AgentFileVersion.agent_id == agent_id, AgentFileVersion.name == name
        )
    )
    return found or 0


def compare(session: Session, agent_id: int, name: str, old: int, new: int) -> str:
    before, after = read(session, agent_id, name, old), read(session, agent_id, name, new)
    return "".join(
        difflib.unified_diff(
            before["content"].splitlines(keepends=True),
            after["content"].splitlines(keepends=True),
            f"{name} version {old}",
            f"{name} version {new}",
        )
    )


def write_version(session: Session, agent_id: int, name: str, content: str, origin: str) -> int:
    """A new version, unless the content is the latest one already; logs the size, never the content."""
    if len(content) > AGENT_FILE_MAX:
        raise ValueError(f"fichier {name} : {len(content)} caractères, {AGENT_FILE_MAX} au plus")
    current = read(session, agent_id, name)
    if current["version"] and current["content"] == content:
        return current["version"]
    number = current["version"] + 1
    session.add(AgentFileVersion(agent_id=agent_id, name=name, version=number, content=content, origin=origin))
    session.flush()
    logger.info("agent %s fichier %s version %d, %d caractères, %s", agent_id, name, number, len(content), origin)
    return number


def with_entries(content: str, entries: list[tuple[str, str, str]]) -> str:
    """The file with each (key, title, text): a key already there is replaced in place, a new one appended."""
    parts = ENTRY.split(content)
    keyed = dict(zip(parts[1::2], parts[2::2]))
    for key, title, text in entries:
        keyed[key] = f"## {title}\n\n{text.strip()}\n\n"
    return parts[0] + "".join(f"<!-- entree: {k} -->\n{block}" for k, block in keyed.items())


def output_errors(files: object, declared: list[str], fed: set[str]) -> list[str]:
    """What is wrong with the files a run hands back: undeclared, oversized, duplicated, or also fed by productions."""
    if not isinstance(files, list):
        return ["files : attendu une liste de {name, content}."]
    errors, seen = [], set()
    for i, f in enumerate(files):
        path = f"files[{i}]"
        if not (isinstance(f, dict) and set(f) == {"name", "content"} and isinstance(f["content"], str)):
            errors.append(f"{path} : attendu exactement name et content (un texte).")
        elif f["name"] not in declared:
            errors.append(f"{path} : {f['name']!r} n'est pas un fichier déclaré de l'agent.")
        elif len(f["content"]) > AGENT_FILE_MAX:
            errors.append(f"{path} : {len(f['content'])} caractères, {AGENT_FILE_MAX} au plus.")
        elif f["name"] in seen or f["name"] in fed:
            errors.append(f"{path} : {f['name']} est rendu deux fois ou reçoit aussi des productions de ce run.")
        else:
            seen.add(f["name"])
    return errors
