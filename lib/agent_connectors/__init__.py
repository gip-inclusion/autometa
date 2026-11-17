"""Preparation connectors: one generic interface, one file per type, the closed list of types in config."""

import importlib
from functools import cache
from types import ModuleType

import yaml

from web import config

__all__ = ["types", "catalogue", "errors", "label", "prepare", "bounded_int", "names_errors", "cut"]

# Why: what one preparation may weigh in the run's input, in characters: low, high, default.
CAP = (1_000, 200_000, 60_000)


@cache
def types() -> tuple[str, ...]:
    """Why: the closed list ships with the code; it is read once per process, not at every validation."""
    return tuple(yaml.safe_load((config.BASE_DIR / "config" / "agent_preparations.yaml").read_text())["types"])


def connector(kind: str) -> ModuleType:
    # Why: a new type is one file named after it plus one line in config/agent_preparations.yaml,
    # so the closed list in config chooses the module; nothing outside that list is ever imported.
    if kind not in types():
        raise ValueError(f"type de préparation {kind!r} hors de config/agent_preparations.yaml")
    return importlib.import_module(f"lib.agent_connectors.{kind}")


def catalogue() -> dict[str, dict]:
    """Each type with what it reads and its fields; every type also takes cap."""
    return {
        kind: {"description": (c := connector(kind)).DESCRIPTION, "fields": {**c.FIELDS, "cap": cap_help()}}
        for kind in types()
    }


def cap_help() -> str:
    return f"facultatif, taille maximale du contenu en caractères, {CAP[0]} à {CAP[1]}, {CAP[2]} par défaut"


def bounded_int(field: str, value: object, low: int, high: int) -> list[str]:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return [f"{field} : attendu un entier de {low} à {high}."]
    return []


def names_errors(field: str, value: object, high: int) -> list[str]:
    if not (isinstance(value, list) and 1 <= len(value) <= high and all(isinstance(v, str) and v for v in value)):
        return [f"{field} : attendu une liste de 1 à {high} noms."]
    return []


def errors(index: int, step: object) -> list[str]:
    """Every error of one preparation, prefixed with its place in the configuration."""
    path = f"preparations[{index}]"
    if not isinstance(step, dict) or step.get("type") not in types():
        return [f"{path} : attendu un type parmi {', '.join(types())} (voir la commande destinations)."]
    c = connector(step["type"])
    if unknown := sorted(set(step) - {"type", "cap", *c.FIELDS}):
        fields = ", ".join(c.FIELDS)
        return [f"{path} : champs inconnus pour {step['type']} : {', '.join(unknown)} ; champs : {fields}."]
    found = bounded_int("cap", step["cap"], *CAP[:2]) if "cap" in step else []
    return [f"{path}.{e}" for e in found + c.errors(step)]


def label(step: dict) -> str:
    return f"{step['type']} {connector(step['type']).source(step)}"


def cut(text: str, cap: int, what: str = "contenu") -> str:
    if len(text) <= cap:
        return text
    return text[:cap] + f"\n\n[{what} tronqué à {cap} caractères sur {len(text)}]"


def prepare(step: dict, cursor: int = 0) -> dict:
    """One preparation's source and Markdown content within its cap; some also say where the next run resumes."""
    cap = step.get("cap", CAP[2])
    found = connector(step["type"]).prepare(step, cap, cursor)
    return {"source": label(step).partition(" ")[2], **found, "content": cut(found["content"], cap)}
