"""Preparation notion: a database (filtered, narrowed, digested beyond the cap) or a page and its sub-pages, as Markdown."""

import re
from collections import Counter

import httpx

from lib import notion
from lib.agent_connectors import bounded_int, names_errors

DESCRIPTION = (
    "une base Notion (base) ou une page et ses sous-pages (page), partagée avec l'intégration Notion d'Autometa"
)
FIELDS = {
    "base": "identifiant d'une base (32 caractères hexadécimaux) ; base ou page, pas les deux",
    "page": "identifiant d'une page ; base ou page, pas les deux",
    "filter": "base : liste de conditions {column, et un opérateur parmi equals, in, contains, after, before}",
    "columns": "base : colonnes gardées (30 au plus) ; toutes par défaut",
    "group_by": "base : colonnes à décompter quand la base dépasse le plafond (5 au plus) ; choisies sinon",
    "depth": "page : niveaux de sous-pages ouverts, 1 à 3, 2 par défaut",
}
OPERATORS = ("equals", "in", "contains", "after", "before")
DATE_COLUMN = "derniere_modification"
BASE_ONLY, PAGE_ONLY = ("filter", "columns", "group_by"), ("depth",)


def filter_errors(conditions: object) -> list[str]:
    ops = ", ".join(OPERATORS)
    if not isinstance(conditions, list) or not 1 <= len(conditions) <= 10:
        return [f"filter : attendu de 1 à 10 conditions, chacune column et un opérateur parmi {ops}."]
    errors = []
    for i, condition in enumerate(conditions):
        used = set(condition) - {"column"} if isinstance(condition, dict) else set()
        if not (isinstance(condition, dict) and isinstance(condition.get("column"), str) and len(used) == 1):
            errors.append(f"filter[{i}] : attendu column et exactement un opérateur parmi {ops}.")
            continue
        (op,) = used
        value = condition[op]
        valid = {
            "equals": isinstance(value, (str, int, float, bool)),
            "in": isinstance(value, list) and 1 <= len(value) <= 30,
            "contains": isinstance(value, str) and bool(value),
            "after": re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)) is not None,
            "before": re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)) is not None,
        }.get(op)
        if valid is None:
            errors.append(f"filter[{i}].{op} : opérateur inconnu, opérateurs : {ops}.")
        elif not valid:
            errors.append(f"filter[{i}].{op} : valeur invalide (after, before : une date AAAA-MM-JJ ; in : une liste).")
    return errors


def errors(step: dict) -> list[str]:
    kind = "base" if "base" in step else "page"
    if ("base" in step) == ("page" in step):
        return ["base ou page : attendu exactement l'un des deux."]
    if not (isinstance(step[kind], str) and re.fullmatch(r"[0-9a-f]{32}|[0-9a-f-]{36}", step[kind])):
        return [f"{kind} : attendu l'identifiant Notion (32 caractères hexadécimaux)."]
    if misplaced := [f for f in (PAGE_ONLY if kind == "base" else BASE_ONLY) if f in step]:
        return [f"{', '.join(misplaced)} : sans objet pour une {kind}."]
    found = filter_errors(step["filter"]) if "filter" in step else []
    for name, high in (("columns", 30), ("group_by", 5)):
        if name in step:
            found += names_errors(name, step[name], high)
    if "depth" in step:
        found += bounded_int("depth", step["depth"], 1, 3)
    return found


def source(step: dict) -> str:
    return f"base {step['base']}" if "base" in step else f"page {step['page']}"


def as_list(value: object) -> list:
    return value if isinstance(value, list) else [value]


def matches(row: dict, condition: dict) -> bool:
    (op,) = set(condition) - {"column"}
    value, expected = row.get(condition["column"]), condition[op]
    if op == "equals":
        return expected in as_list(value)
    if op == "in":
        return any(v in expected for v in as_list(value))
    if op == "contains":
        return any(str(expected).lower() in str(v).lower() for v in as_list(value) if v is not None)
    if value is None:
        return False
    day = str(value)[:10]
    return day >= str(expected) if op == "after" else day < str(expected)


def cell(value: object) -> str:
    text = ", ".join(map(str, value)) if isinstance(value, list) else "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def table(rows: list[dict], columns: list[str]) -> list[str]:
    return [
        "| " + " | ".join(columns) + " |",
        "|" + "---|" * len(columns),
        *("| " + " | ".join(cell(r.get(c)) for c in columns) + " |" for r in rows),
    ]


def digest(rows: list[dict], columns: list[str], groups: list[str], cap: int) -> str:
    """Deterministic digest of rows beyond the cap: counts by group, then the latest rows that fit."""
    groups = groups or [c for c in columns if c != DATE_COLUMN and 2 <= len({cell(r.get(c)) for r in rows}) <= 30]
    lines = [f"{len(rows)} lignes, au-delà du plafond de {cap} caractères : décomptes, puis les plus récentes.", ""]
    for column in groups:
        counts = Counter(str(v) for r in rows for v in as_list(r.get(column)))
        lines += [f"## {column}", *(f"- {value} : {n}" for value, n in counts.most_common()), ""]
    head = [*lines, "## Lignes les plus récentes", *table([], columns)]
    size = len("\n".join(head))
    if size > cap:
        raise ValueError(f"plafond de {cap} caractères trop petit pour le seul décompte ({size})")
    kept = []
    for row in sorted(rows, key=lambda r: str(r.get(DATE_COLUMN) or ""), reverse=True):
        size += len(table([row], columns)[-1]) + 1
        if size > cap:
            break
        kept.append(row)
    return "\n".join([*lines, "## Lignes les plus récentes", *table(kept, columns)])


def base(step: dict, cap: int) -> str:
    pages = notion.query_database(step["base"])
    rows = [{**notion.extract_page_properties(p), DATE_COLUMN: (p.get("last_edited_time") or "")[:10]} for p in pages]
    if not rows:
        return "(base vide)"
    known = list(rows[0])
    named = [c["column"] for c in step.get("filter", [])] + step.get("columns", []) + step.get("group_by", [])
    if missing := sorted(set(named) - set(known)):
        raise ValueError(
            f"préparation notion base {step['base']} : colonnes absentes : {', '.join(missing)} ; "
            f"colonnes de la base : {', '.join(known)}"
        )
    rows = [r for r in rows if all(matches(r, c) for c in step.get("filter", []))]
    columns = [*step["columns"], DATE_COLUMN] if "columns" in step else known
    text = "\n".join([f"{len(rows)} lignes.", "", *table(rows, columns)])
    return text if len(text) <= cap else digest(rows, columns, step.get("group_by", []), cap)


def prepare(step: dict, cap: int, cursor: int) -> dict:
    """Why: Notion answers 403 or 404 for a base or page never shared with the integration."""
    if not notion.NOTION_TOKEN:
        raise ValueError("préparation notion : NOTION_TOKEN absent, Notion n'est pas configuré sur cette instance")
    try:
        if "base" in step:
            return {"content": base(step, cap)}
        return {"content": notion.page_markdown(step["page"], step.get("depth", 2))}
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (403, 404):
            raise ValueError(
                f"préparation notion {source(step)} : introuvable ou non partagée avec l'intégration Notion "
                "d'Autometa (dans Notion : ••• > Connexions > ajouter l'intégration)"
            ) from exc
        raise
