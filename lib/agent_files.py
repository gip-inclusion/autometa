"""An agent's own files, kept by Autometa in S3 and versioned: never sent outside, written only if declared."""

import difflib
import logging
import re
from datetime import datetime

from lib.agent_config import FICHIER_MAX
from lib.agent_delivery import read_json, write_json

logger = logging.getLogger(__name__)

__all__ = ["read", "history", "compare", "write_version", "add_entries", "output_errors"]

ENTRY = re.compile(r"(?m)^<!-- entree: ([0-9a-z-]+) -->\n")


def index_path(slug: str, nom: str) -> str:
    return f"{slug}/fichiers/{nom}/index.json"


def history(slug: str, nom: str) -> list[dict]:
    """Every version of a file, oldest first: number, date, origin, size; never the content."""
    return (read_json(index_path(slug, nom)) or {"versions": []})["versions"]


def read(slug: str, nom: str, version: int | None = None) -> dict:
    """A version of a file, the latest by default; version 0 is the empty file before any write."""
    versions = history(slug, nom)
    number = version if version is not None else len(versions)
    if not 0 <= number <= len(versions):
        raise ValueError(f"fichier {nom} : version {number} inconnue, versions 1 à {len(versions)}")
    if number == 0:
        return {"nom": nom, "version": 0, "contenu": ""}
    return {**versions[number - 1], "nom": nom, **read_json(f"{slug}/fichiers/{nom}/{number:04d}.json")}


def compare(slug: str, nom: str, de: int, a: int) -> str:
    before, after = read(slug, nom, de), read(slug, nom, a)
    return "".join(
        difflib.unified_diff(
            before["contenu"].splitlines(keepends=True),
            after["contenu"].splitlines(keepends=True),
            f"{nom} version {de}",
            f"{nom} version {a}",
        )
    )


def write_version(slug: str, nom: str, contenu: str, origine: str) -> int:
    """A new version, unless the content is the latest one already; logs the size, never the content."""
    if len(contenu) > FICHIER_MAX:
        raise ValueError(f"fichier {nom} : {len(contenu)} caractères, {FICHIER_MAX} au plus")
    versions = history(slug, nom)
    if versions and read(slug, nom)["contenu"] == contenu:
        return len(versions)
    number = len(versions) + 1
    write_json(f"{slug}/fichiers/{nom}/{number:04d}.json", {"contenu": contenu})
    meta = {
        "version": number,
        "ecrit_le": datetime.now().isoformat(timespec="seconds"),
        "origine": origine,
        "taille": len(contenu),
    }
    write_json(index_path(slug, nom), {"versions": [*versions, meta]})
    logger.info("agent %s fichier %s version %d, %d caractères, %s", slug, nom, number, len(contenu), origine)
    return number


def add_entries(slug: str, nom: str, entries: list[tuple[str, str, str]], origine: str) -> int:
    """Put each (key, title, text) in the file: a key already there is replaced in place, a new one appended."""
    parts = ENTRY.split(read(slug, nom)["contenu"])
    keyed = dict(zip(parts[1::2], parts[2::2]))
    for key, titre, texte in entries:
        keyed[key] = f"## {titre}\n\n{texte.strip()}\n\n"
    contenu = parts[0] + "".join(f"<!-- entree: {k} -->\n{block}" for k, block in keyed.items())
    return write_version(slug, nom, contenu, origine)


def output_errors(fichiers: object, declared: list[str], fed: set[str]) -> list[str]:
    """What is wrong with the files a run hands back: undeclared, oversized, duplicated, or also fed by productions."""
    if not isinstance(fichiers, list):
        return ["fichiers : attendu une liste de {nom, contenu}."]
    errors, seen = [], set()
    for i, f in enumerate(fichiers):
        path = f"fichiers[{i}]"
        if not (isinstance(f, dict) and set(f) == {"nom", "contenu"} and isinstance(f["contenu"], str)):
            errors.append(f"{path} : attendu exactement nom et contenu (un texte).")
        elif f["nom"] not in declared:
            errors.append(f"{path} : {f['nom']!r} n'est pas un fichier déclaré de l'agent.")
        elif len(f["contenu"]) > FICHIER_MAX:
            errors.append(f"{path} : {len(f['contenu'])} caractères, {FICHIER_MAX} au plus.")
        elif f["nom"] in seen or f["nom"] in fed:
            errors.append(f"{path} : {f['nom']} est rendu deux fois ou reçoit aussi des productions de ce run.")
        else:
            seen.add(f["nom"])
    return errors
