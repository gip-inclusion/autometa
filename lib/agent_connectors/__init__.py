"""Preparation connectors: one generic interface, one file per type, the closed list of types in config."""

import importlib
from types import ModuleType

import yaml

from web import config

__all__ = ["types", "catalogue", "errors", "label", "prepare", "bounded_int", "names_errors", "cut"]

# Why: what one preparation may weigh in the run's input, in characters: low, high, default.
PLAFOND = (1_000, 200_000, 60_000)


def types() -> list[str]:
    return yaml.safe_load((config.BASE_DIR / "config" / "agent_preparations.yaml").read_text())["types"]


def connector(kind: str) -> ModuleType:
    # Why: a new type is one file named after it plus one line in config/agent_preparations.yaml,
    # so the closed list in config chooses the module; nothing outside that list is ever imported.
    if kind not in types():
        raise ValueError(f"type de préparation {kind!r} hors de config/agent_preparations.yaml")
    return importlib.import_module(f"lib.agent_connectors.{kind}")


def catalogue() -> dict[str, dict]:
    """Each type with what it reads and its fields; every type also takes plafond."""
    return {
        kind: {"description": (c := connector(kind)).DESCRIPTION, "champs": {**c.CHAMPS, "plafond": cap_help()}}
        for kind in types()
    }


def cap_help() -> str:
    return f"facultatif, taille maximale du contenu en caractères, {PLAFOND[0]} à {PLAFOND[1]}, {PLAFOND[2]} par défaut"


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
    if unknown := sorted(set(step) - {"type", "plafond", *c.CHAMPS}):
        fields = ", ".join(c.CHAMPS)
        return [f"{path} : champs inconnus pour {step['type']} : {', '.join(unknown)} ; champs : {fields}."]
    found = bounded_int("plafond", step["plafond"], *PLAFOND[:2]) if "plafond" in step else []
    return [f"{path}.{e}" for e in found + c.errors(step)]


def label(step: dict) -> str:
    return f"{step['type']} {connector(step['type']).source(step)}"


def cut(text: str, plafond: int, what: str = "contenu") -> str:
    if len(text) <= plafond:
        return text
    return text[:plafond] + f"\n\n[{what} tronqué à {plafond} caractères sur {len(text)}]"


def prepare(step: dict, debut: int = 0) -> dict:
    """One preparation's source and Markdown content within its cap; some also say where the next run resumes."""
    plafond = step.get("plafond", PLAFOND[2])
    found = connector(step["type"]).prepare(step, plafond, debut)
    return {"source": label(step).partition(" ")[2], **found, "contenu": cut(found["contenu"], plafond)}
