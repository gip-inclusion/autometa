"""Agent configuration, format pdi.agent/1: strict YAML reading and validation against the closed destination list."""

import difflib
import json
import logging
import re

import yaml

from web import config

logger = logging.getLogger(__name__)

__all__ = [
    "CADENCES",
    "CHAMP_TYPES",
    "FORMAT",
    "MODES",
    "destinations",
    "modeles",
    "PREPARATION_TYPES",
    "parse",
    "target_gaps",
    "validate",
    "warn_target_gaps",
]

FORMAT = "pdi.agent/1"
MODES = ("ombre", "relecture", "reel")
FIELDS = ("format", "slug", "titre", "mission", "points_de_contact")
OPTIONAL_FIELDS = ("cadence", "outils_modeles", "preparations")
CADENCES = {"quotidienne": "daily", "hebdomadaire": "weekly", "mensuelle": "monthly"}
# Why: the closed set of what may feed an agent's run, each with its one parameter; no code per agent.
PREPARATION_TYPES = {"notion": "base", "s3": "jeu", "cron": "tache"}
GENERIC_CRON = "run-agents"
# Why: what an extraction may declare, flat on purpose; each maps to its JSON Schema type for Ollama.
CHAMP_TYPES = {"texte": "string", "nombre": "number", "entier": "integer", "booleen": "boolean"}
# Why: the type-specific fields of a sub-agent, besides type and modele.
SUBAGENT_FIELDS = {"classificateur": ("question", "seuil"), "extraction": ("schema",), "resume": ("longueur_max",)}
# Why: the mission is the only free text an LLM writes; a link, a person or a channel there would bypass
# the closed destination list.
FORBIDDEN_FREE_TEXT = re.compile(
    r"https?://|www\.|@[\w.-]+|#[\w-]+|\b[\w.+-]+@[\w-]+\.\w+|\b[CDG][A-Z0-9]{8,}\b|\bxox[a-z]-"
)


class StrictLoader(yaml.SafeLoader):
    """SafeLoader refusing duplicate keys, which PyYAML would silently overwrite."""


def mapping_without_duplicates(loader: StrictLoader, node: yaml.MappingNode) -> dict:
    keys = [loader.construct_object(key) for key, _ in node.value]
    if duplicates := sorted({str(k) for k in keys if keys.count(k) > 1}):
        raise yaml.constructor.ConstructorError(None, None, f"clé en double : {', '.join(duplicates)}", node.start_mark)
    return loader.construct_mapping(node)


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping_without_duplicates)


def parse(text: str) -> object:
    loader = StrictLoader(text)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


def closed_list(name: str) -> dict[str, dict]:
    raw = yaml.safe_load((config.BASE_DIR / "config" / f"agent_{name}.yaml").read_text())
    return {d["id"]: d for d in raw[name]}


def destinations() -> dict[str, dict]:
    """The closed list of destinations, by id."""
    return closed_list("destinations")


def modeles() -> dict[str, list[str]]:
    """The closed list of sub-agent types, each with the Ollama Cloud models it may use."""
    raw = yaml.safe_load((config.BASE_DIR / "config" / "agent_modeles.yaml").read_text())
    return {t["type"]: t["modeles"] for t in raw["types"]}


def target_gaps() -> tuple[list[str], list[str]]:
    """Destinations without a real id in AGENT_DESTINATION_TARGETS, and ids there naming no known destination."""
    known, targets = set(destinations()), config.AGENT_DESTINATION_TARGETS
    return sorted(d for d in known if not targets.get(d)), sorted(set(targets) - known)


def warn_target_gaps() -> None:
    """Why: a gap only fails the deliveries it concerns, so startup warns and never stops."""
    missing, unknown = target_gaps()
    if missing:
        logger.warning("destinations d'agent sans cible dans AGENT_DESTINATION_TARGETS : %s", ", ".join(missing))
    if unknown:
        logger.warning("AGENT_DESTINATION_TARGETS cite des destinations inconnues : %s", ", ".join(unknown))


def suggestion(value: object, choices: list[str]) -> str:
    close = difflib.get_close_matches(str(value), choices, n=1, cutoff=0.6)
    return f" Vouliez-vous dire {close[0]!r} ?" if close else ""


def text_errors(doc: dict, field: str, low: int, high: int) -> list[str]:
    value = doc[field]
    if not isinstance(value, str) or not low <= len(value) <= high:
        return [f"{field} : attendu un texte de {low} à {high} caractères."]
    return []


def free_text_errors(field: str, value: object, hint: str) -> list[str]:
    if isinstance(value, str) and (found := FORBIDDEN_FREE_TEXT.search(value)):
        return [f"{field} : contient {found.group(0)!r}. Ni lien, ni personne, ni canal : {hint}"]
    return []


def schema_errors(path: str, schema: object) -> list[str]:
    kinds = ", ".join(CHAMP_TYPES)
    if not isinstance(schema, dict) or not 1 <= len(schema) <= 10:
        return [f"{path}.schema : attendu de 1 à 10 champs, chacun nom: type parmi {kinds}."]
    return [
        f"{path}.schema.{k} : nom en minuscules et soulignés, type parmi {kinds}."
        for k, t in schema.items()
        if not (isinstance(k, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,39}", k) and str(t) in CHAMP_TYPES)
    ]


def outil_errors(index: int, outil: object, known: dict[str, list[str]]) -> list[str]:
    path = f"outils_modeles[{index}]"
    if not isinstance(outil, dict) or outil.get("type") not in known:
        return [f"{path}.type : attendu un type de config/agent_modeles.yaml parmi {', '.join(known)}."]
    kind, fields = outil["type"], SUBAGENT_FIELDS[outil["type"]]
    if set(outil) != {"type", "modele", *fields}:
        return [f"{path} : un sous-agent {kind} a exactement les champs type, modele, {', '.join(fields)}."]
    if outil["modele"] not in known[kind]:
        return [
            f"{path}.modele : {outil['modele']!r} n'est pas permis pour {kind}, modèles permis : "
            f"{', '.join(known[kind])}.{suggestion(outil['modele'], known[kind])}"
        ]
    if kind == "extraction":
        return schema_errors(path, outil["schema"])
    if kind == "resume":
        limite = outil["longueur_max"]
        if isinstance(limite, bool) or not isinstance(limite, int) or not 100 <= limite <= 3000:
            return [f"{path}.longueur_max : attendu un nombre de caractères de 100 à 3000."]
        return []
    errors = text_errors(outil, "question", 10, 300)
    errors += free_text_errors(f"{path}.question", outil["question"], "la question porte sur une production.")
    seuil = outil["seuil"]
    if isinstance(seuil, bool) or not isinstance(seuil, (int, float)) or not 0 < seuil < 1:
        errors.append(f"{path}.seuil : attendu une probabilité strictement entre 0 et 1, par exemple 0.7.")
    return [e if e.startswith(path) else f"{path}.{e}" for e in errors]


def list_errors(field: str, items: object, high: int, keys: list[str]) -> list[str]:
    if not isinstance(items, list) or len(items) > high:
        return [f"{field} : attendu une liste de {high} éléments au plus."]
    return [f"{field} : {k!r} apparaît plusieurs fois." for k in sorted({k for k in keys if keys.count(k) > 1})]


def preparation_label(step: dict) -> str:
    return f"{step.get('type')} {step.get(PREPARATION_TYPES.get(step.get('type'), ''))}"


def cron_tasks() -> list[str]:
    """Tasks of cron/ whose last output a preparation may read; the generic agents cron is not one."""
    return sorted(d.name for d in config.CRON_DIR.iterdir() if (d / "cron.py").is_file() and d.name != GENERIC_CRON)


def preparation_errors(index: int, step: object) -> list[str]:
    path = f"preparations[{index}]"
    kinds = ", ".join(f"{t} (avec {p})" for t, p in PREPARATION_TYPES.items())
    if not isinstance(step, dict) or step.get("type") not in PREPARATION_TYPES:
        return [f"{path} : attendu un type parmi {kinds}."]
    param = PREPARATION_TYPES[step["type"]]
    if set(step) != {"type", param}:
        return [f"{path} : une préparation {step['type']} a exactement les champs type et {param}."]
    value = step[param]
    if step["type"] == "notion" and not (isinstance(value, str) and re.fullmatch(r"[0-9a-f]{32}|[0-9a-f-]{36}", value)):
        return [f"{path}.base : attendu l'identifiant d'une base Notion (32 caractères hexadécimaux)."]
    if step["type"] == "s3" and not (
        isinstance(value, str) and re.fullmatch(r"[a-z0-9][a-z0-9_-]*\.(sqlite|jsonl|csv)", value)
    ):
        return [f"{path}.jeu : attendu un fichier publié par publish_dataset, par exemple services.sqlite."]
    if step["type"] == "cron" and value not in (tasks := cron_tasks()):
        return [f"{path}.tache : {value!r} n'est pas une tâche de cron/.{suggestion(value, tasks)}"]
    return []


def contact_errors(slug: object, index: int, contact: object, known: dict[str, dict]) -> list[str]:
    path = f"points_de_contact[{index}]"
    if not isinstance(contact, dict) or set(contact) != {"id", "mode"}:
        return [f"{path} : attendu exactement les champs id et mode."]
    destination = known.get(contact["id"])
    if destination is None:
        return [
            f"{path}.id : {contact['id']!r} n'est pas une destination de config/agent_destinations.yaml. "
            f"Un agent ne nomme ni canal ni personne : il choisit une destination de la liste."
            f"{suggestion(contact['id'], list(known))}"
        ]
    if contact["mode"] not in MODES:
        return [f"{path}.mode : {contact['mode']!r} inconnu, modes permis : {', '.join(MODES)}."]
    if contact["mode"] == "reel" and slug not in destination["reel_autorise"]:
        return [
            f"{path}.mode : le mode reel sur {contact['id']!r} n'est pas ouvert à cet agent. "
            "Il s'ouvre par une PR qui l'ajoute à reel_autorise dans config/agent_destinations.yaml."
        ]
    return []


def validate(doc: object) -> list[str]:
    """Every error of an agent configuration, each naming its field and the fix; empty when accepted."""
    if not isinstance(doc, dict):
        return ["(racine) : la configuration doit être un objet YAML (clé: valeur)."]
    known_fields = FIELDS + OPTIONAL_FIELDS
    errors = [f"{k} : champ obligatoire absent." for k in FIELDS if k not in doc]
    errors += [
        f"{k} : champ inconnu, le format est fermé.{suggestion(k, list(known_fields))}"
        for k in doc
        if k not in known_fields
    ]
    if "format" in doc and doc["format"] != FORMAT:
        errors.append(f"format : doit valoir {FORMAT!r}.")
    if "slug" in doc and not (isinstance(doc["slug"], str) and re.fullmatch(r"[a-z][a-z0-9-]{2,40}", doc["slug"])):
        errors.append("slug : minuscules, chiffres et tirets, de 3 à 41 caractères, commençant par une lettre.")
    if "titre" in doc:
        errors += text_errors(doc, "titre", 3, 80)
    if "mission" in doc:
        errors += text_errors(doc, "mission", 20, 400)
        errors += free_text_errors("mission", doc["mission"], "une destination se déclare dans points_de_contact.")
    if "cadence" in doc and doc["cadence"] not in CADENCES:
        errors.append(f"cadence : {doc['cadence']!r} inconnue, cadences permises : {', '.join(CADENCES)}.")
    if "outils_modeles" in doc:
        outils = doc["outils_modeles"]
        keys = [json.dumps(o, sort_keys=True, default=str) for o in outils] if isinstance(outils, list) else []
        errors += list_errors("outils_modeles", outils, 3, keys)
        known_models = modeles()
        errors += [
            e
            for i, o in enumerate(outils if isinstance(outils, list) else [])
            for e in outil_errors(i, o, known_models)
        ]
    if "preparations" in doc:
        steps = doc["preparations"] if isinstance(doc["preparations"], list) else []
        keys = [preparation_label(p) for p in steps if isinstance(p, dict)]
        errors += list_errors("preparations", doc["preparations"], 3, keys)
        errors += [e for i, p in enumerate(steps) for e in preparation_errors(i, p)]
    if "points_de_contact" in doc:
        contacts = doc["points_de_contact"]
        if not isinstance(contacts, list) or not 1 <= len(contacts) <= 6:
            return [*errors, "points_de_contact : attendu une liste de 1 à 6 destinations."]
        known = destinations()
        for i, contact in enumerate(contacts):
            errors += contact_errors(doc.get("slug"), i, contact, known)
        ids = [c["id"] for c in contacts if isinstance(c, dict) and "id" in c]
        errors += [
            f"points_de_contact : {d!r} apparaît plusieurs fois." for d in sorted({i for i in ids if ids.count(i) > 1})
        ]
    return errors
