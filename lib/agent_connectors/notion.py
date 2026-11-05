"""Preparation notion: a database (filtered, narrowed, digested beyond the cap) or a page and its sub-pages, as Markdown."""

import re
from collections import Counter

import httpx

from lib import notion
from lib.agent_connectors import bounded_int, names_errors

DESCRIPTION = (
    "une base Notion (base) ou une page et ses sous-pages (page), partagée avec l'intégration Notion d'Autometa"
)
CHAMPS = {
    "base": "identifiant d'une base (32 caractères hexadécimaux) ; base ou page, pas les deux",
    "page": "identifiant d'une page ; base ou page, pas les deux",
    "filtre": "base : liste de conditions {colonne, et un opérateur parmi egal, parmi, contient, apres, avant}",
    "colonnes": "base : colonnes gardées (30 au plus) ; toutes par défaut",
    "regrouper_par": "base : colonnes à décompter quand la base dépasse le plafond (5 au plus) ; choisies sinon",
    "profondeur": "page : niveaux de sous-pages ouverts, 1 à 3, 2 par défaut",
}
OPERATEURS = ("egal", "parmi", "contient", "apres", "avant")
DATE_COLUMN = "derniere_modification"
BASE_ONLY, PAGE_ONLY = ("filtre", "colonnes", "regrouper_par"), ("profondeur",)


def filtre_errors(conditions: object) -> list[str]:
    ops = ", ".join(OPERATEURS)
    if not isinstance(conditions, list) or not 1 <= len(conditions) <= 10:
        return [f"filtre : attendu de 1 à 10 conditions, chacune colonne et un opérateur parmi {ops}."]
    errors = []
    for i, condition in enumerate(conditions):
        used = set(condition) - {"colonne"} if isinstance(condition, dict) else set()
        if not (isinstance(condition, dict) and isinstance(condition.get("colonne"), str) and len(used) == 1):
            errors.append(f"filtre[{i}] : attendu colonne et exactement un opérateur parmi {ops}.")
            continue
        (op,) = used
        value = condition[op]
        valid = {
            "egal": isinstance(value, (str, int, float, bool)),
            "parmi": isinstance(value, list) and 1 <= len(value) <= 30,
            "contient": isinstance(value, str) and bool(value),
            "apres": re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)) is not None,
            "avant": re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)) is not None,
        }.get(op)
        if valid is None:
            errors.append(f"filtre[{i}].{op} : opérateur inconnu, opérateurs : {ops}.")
        elif not valid:
            errors.append(
                f"filtre[{i}].{op} : valeur invalide (apres, avant : une date AAAA-MM-JJ ; parmi : une liste)."
            )
    return errors


def errors(step: dict) -> list[str]:
    kind = "base" if "base" in step else "page"
    if ("base" in step) == ("page" in step):
        return ["base ou page : attendu exactement l'un des deux."]
    if not (isinstance(step[kind], str) and re.fullmatch(r"[0-9a-f]{32}|[0-9a-f-]{36}", step[kind])):
        return [f"{kind} : attendu l'identifiant Notion (32 caractères hexadécimaux)."]
    if misplaced := [f for f in (PAGE_ONLY if kind == "base" else BASE_ONLY) if f in step]:
        return [f"{', '.join(misplaced)} : sans objet pour une {kind}."]
    found = filtre_errors(step["filtre"]) if "filtre" in step else []
    for name, high in (("colonnes", 30), ("regrouper_par", 5)):
        if name in step:
            found += names_errors(name, step[name], high)
    if "profondeur" in step:
        found += bounded_int("profondeur", step["profondeur"], 1, 3)
    return found


def source(step: dict) -> str:
    return f"base {step['base']}" if "base" in step else f"page {step['page']}"


def as_list(value: object) -> list:
    return value if isinstance(value, list) else [value]


def matches(row: dict, condition: dict) -> bool:
    (op,) = set(condition) - {"colonne"}
    value, expected = row.get(condition["colonne"]), condition[op]
    if op == "egal":
        return expected in as_list(value)
    if op == "parmi":
        return any(v in expected for v in as_list(value))
    if op == "contient":
        return any(str(expected).lower() in str(v).lower() for v in as_list(value) if v is not None)
    if value is None:
        return False
    day = str(value)[:10]
    return day >= str(expected) if op == "apres" else day < str(expected)


def cell(value: object) -> str:
    text = ", ".join(map(str, value)) if isinstance(value, list) else "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def table(rows: list[dict], columns: list[str]) -> list[str]:
    return [
        "| " + " | ".join(columns) + " |",
        "|" + "---|" * len(columns),
        *("| " + " | ".join(cell(r.get(c)) for c in columns) + " |" for r in rows),
    ]


def digest(rows: list[dict], columns: list[str], groupes: list[str], plafond: int) -> str:
    """Deterministic digest of rows beyond the cap: counts by group, then the latest rows that fit."""
    groupes = groupes or [c for c in columns if c != DATE_COLUMN and 2 <= len({cell(r.get(c)) for r in rows}) <= 30]
    lines = [f"{len(rows)} lignes, au-delà du plafond de {plafond} caractères : décomptes, puis les plus récentes.", ""]
    for column in groupes:
        counts = Counter(str(v) for r in rows for v in as_list(r.get(column)))
        lines += [f"## {column}", *(f"- {value} : {n}" for value, n in counts.most_common()), ""]
    head = [*lines, "## Lignes les plus récentes", *table([], columns)]
    size = len("\n".join(head))
    if size > plafond:
        raise ValueError(f"plafond de {plafond} caractères trop petit pour le seul décompte ({size})")
    kept = []
    for row in sorted(rows, key=lambda r: str(r.get(DATE_COLUMN) or ""), reverse=True):
        size += len(table([row], columns)[-1]) + 1
        if size > plafond:
            break
        kept.append(row)
    return "\n".join([*lines, "## Lignes les plus récentes", *table(kept, columns)])


def base(step: dict, plafond: int) -> str:
    pages = notion.query_database(step["base"])
    rows = [{**notion.extract_page_properties(p), DATE_COLUMN: (p.get("last_edited_time") or "")[:10]} for p in pages]
    if not rows:
        return "(base vide)"
    known = list(rows[0])
    named = [c["colonne"] for c in step.get("filtre", [])] + step.get("colonnes", []) + step.get("regrouper_par", [])
    if missing := sorted(set(named) - set(known)):
        raise ValueError(
            f"préparation notion base {step['base']} : colonnes absentes : {', '.join(missing)} ; "
            f"colonnes de la base : {', '.join(known)}"
        )
    rows = [r for r in rows if all(matches(r, c) for c in step.get("filtre", []))]
    columns = [*step["colonnes"], DATE_COLUMN] if "colonnes" in step else known
    text = "\n".join([f"{len(rows)} lignes.", "", *table(rows, columns)])
    return text if len(text) <= plafond else digest(rows, columns, step.get("regrouper_par", []), plafond)


def prepare(step: dict, plafond: int, debut: int) -> dict:
    """Why: Notion answers 403 or 404 for a base or page never shared with the integration."""
    if not notion.NOTION_TOKEN:
        raise ValueError("préparation notion : NOTION_TOKEN absent, Notion n'est pas configuré sur cette instance")
    try:
        if "base" in step:
            return {"contenu": base(step, plafond)}
        return {"contenu": notion.page_markdown(step["page"], step.get("profondeur", 2))}
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (403, 404):
            raise ValueError(
                f"préparation notion {source(step)} : introuvable ou non partagée avec l'intégration Notion "
                "d'Autometa (dans Notion : ••• > Connexions > ajouter l'intégration)"
            ) from exc
        raise
