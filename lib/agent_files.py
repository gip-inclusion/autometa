"""An agent's own files, kept by Autometa in S3 and versioned: never sent outside, written only if declared."""

import difflib
import logging
import re
from datetime import datetime

from lib.agent_config import AGENT_FILE_MAX
from lib.agent_delivery import read_json, write_json

logger = logging.getLogger(__name__)

__all__ = ["read", "history", "compare", "write_version", "add_entries", "output_errors"]

ENTRY = re.compile(r"(?m)^<!-- entree: ([0-9a-z-]+) -->\n")


def index_path(slug: str, name: str) -> str:
    return f"{slug}/fichiers/{name}/index.json"


def history(slug: str, name: str) -> list[dict]:
    """Every version of a file, oldest first: number, date, origin, size; never the content."""
    return (read_json(index_path(slug, name)) or {"versions": []})["versions"]


def read(slug: str, name: str, version: int | None = None) -> dict:
    """A version of a file, the latest by default; version 0 is the empty file before any write."""
    versions = history(slug, name)
    number = version if version is not None else len(versions)
    if not 0 <= number <= len(versions):
        raise ValueError(f"fichier {name} : version {number} inconnue, versions 1 à {len(versions)}")
    if number == 0:
        return {"name": name, "version": 0, "content": ""}
    return {**versions[number - 1], "name": name, **read_json(f"{slug}/fichiers/{name}/{number:04d}.json")}


def compare(slug: str, name: str, old: int, new: int) -> str:
    before, after = read(slug, name, old), read(slug, name, new)
    return "".join(
        difflib.unified_diff(
            before["content"].splitlines(keepends=True),
            after["content"].splitlines(keepends=True),
            f"{name} version {old}",
            f"{name} version {new}",
        )
    )


def write_version(slug: str, name: str, content: str, origin: str) -> int:
    """A new version, unless the content is the latest one already; logs the size, never the content."""
    if len(content) > AGENT_FILE_MAX:
        raise ValueError(f"fichier {name} : {len(content)} caractères, {AGENT_FILE_MAX} au plus")
    versions = history(slug, name)
    if versions and read(slug, name)["content"] == content:
        return len(versions)
    number = len(versions) + 1
    write_json(f"{slug}/fichiers/{name}/{number:04d}.json", {"content": content})
    meta = {
        "version": number,
        "written_at": datetime.now().isoformat(timespec="seconds"),
        "origin": origin,
        "size": len(content),
    }
    write_json(index_path(slug, name), {"versions": [*versions, meta]})
    logger.info("agent %s fichier %s version %d, %d caractères, %s", slug, name, number, len(content), origin)
    return number


def add_entries(slug: str, name: str, entries: list[tuple[str, str, str]], origin: str) -> int:
    """Put each (key, title, text) in the file: a key already there is replaced in place, a new one appended."""
    parts = ENTRY.split(read(slug, name)["content"])
    keyed = dict(zip(parts[1::2], parts[2::2]))
    for key, title, text in entries:
        keyed[key] = f"## {title}\n\n{text.strip()}\n\n"
    content = parts[0] + "".join(f"<!-- entree: {k} -->\n{block}" for k, block in keyed.items())
    return write_version(slug, name, content, origin)


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
