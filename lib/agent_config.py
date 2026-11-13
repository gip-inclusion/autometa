"""Agent configuration, format pdi.agent/1: strict YAML reading and validation against the closed destination list."""

import difflib
import json
import logging
import re
from functools import cache

import yaml

from lib import agent_connectors
from web import config

logger = logging.getLogger(__name__)

__all__ = [
    "SCHEDULES",
    "FIELD_TYPES",
    "AGENT_FILE_MAX",
    "FORMAT",
    "WEEKDAYS",
    "MODES",
    "cadence",
    "describe",
    "known_destinations",
    "initial_errors",
    "models",
    "parse",
    "target_gaps",
    "validate",
    "warn_target_gaps",
]

FORMAT = "pdi.agent/1"
# Why: a mode is a preset of the two flags that matter; reviewing what is never published makes no sense.
MODES = {
    "background": {"can_publish": False, "review_required": False},
    "conversational": {"can_publish": True, "review_required": True},
    "autonomous": {"can_publish": True, "review_required": False},
}
GROUPINGS = ("single", "digest")
FIELDS = ("format", "slug", "title", "mission", "destinations")
OPTIONAL_FIELDS = ("schedule", "subagents", "preparations", "files")
SCHEDULES = ("daily", "weekly", "monthly")
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
AGENT_FILE_MAX = 100_000
# Why: what an extraction may declare, flat on purpose: JSON Schema types, handed to Ollama as they are.
FIELD_TYPES = ("string", "number", "integer", "boolean")
# Why: the type-specific fields of a sub-agent, besides type and model.
SUBAGENT_FIELDS = {
    "classifier": (("question", "threshold"), ("labels", "threshold")),
    "extraction": (("schema",),),
    "summary": (("max_length",),),
}
# Why: clef answers up to 64 questions in one call; ten labels keep one production's verdict readable.
LABELS_MAX = 10
NAME = r"[a-z][a-z0-9_-]{0,39}"
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


@cache
def read_config(name: str) -> dict:
    """Why: the closed lists ship with the code; they are read once per process, not at every validation."""
    return yaml.safe_load((config.BASE_DIR / "config" / f"agent_{name}.yaml").read_text())


def closed_list(name: str) -> dict[str, dict]:
    return {d["id"]: dict(d) for d in read_config(name)[name]}


def known_destinations() -> dict[str, dict]:
    """The closed list of destinations, by id."""
    return closed_list("destinations")


def models() -> dict[str, list[str]]:
    """The closed list of sub-agent types, each with the Ollama Cloud models it may use."""
    return {t["type"]: list(t["models"]) for t in read_config("models")["types"]}


def target_gaps() -> tuple[list[str], list[str]]:
    """Destinations without a real id in AGENT_DESTINATION_TARGETS, and ids there naming no known destination."""
    known, targets = set(known_destinations()), config.AGENT_DESTINATION_TARGETS
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
    kinds = ", ".join(FIELD_TYPES)
    if not isinstance(schema, dict) or not 1 <= len(schema) <= 10:
        return [f"{path}.schema : attendu de 1 à 10 champs, chacun name: type parmi {kinds}."]
    return [
        f"{path}.schema.{k} : name en minuscules et soulignés, type parmi {kinds}."
        for k, t in schema.items()
        if not (isinstance(k, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,39}", k) and str(t) in FIELD_TYPES)
    ]


def subagent_errors(index: int, subagent: object, known: dict[str, list[str]]) -> list[str]:
    path = f"subagents[{index}]"
    if not isinstance(subagent, dict) or subagent.get("type") not in known:
        return [f"{path}.type : attendu un type de config/agent_models.yaml parmi {', '.join(known)}."]
    kind, variants = subagent["type"], SUBAGENT_FIELDS[subagent["type"]]
    if set(subagent) not in [{"type", "model", *fields} for fields in variants]:
        shapes = " ou ".join("type, model, " + ", ".join(fields) for fields in variants)
        return [f"{path} : un sous-agent {kind} a exactement les champs {shapes}."]
    if subagent["model"] not in known[kind]:
        return [
            f"{path}.model : {subagent['model']!r} n'est pas permis pour {kind}, modèles permis : "
            f"{', '.join(known[kind])}.{suggestion(subagent['model'], known[kind])}"
        ]
    if kind == "extraction":
        return schema_errors(path, subagent["schema"])
    if kind == "summary":
        limit = subagent["max_length"]
        if isinstance(limit, bool) or not isinstance(limit, int) or not 100 <= limit <= 3000:
            return [f"{path}.max_length : attendu un nombre de caractères de 100 à 3000."]
        return []
    if "question" in subagent:
        questions = {"question": subagent["question"]}
    else:
        labels = subagent["labels"]
        shaped = isinstance(labels, list) and all(
            isinstance(e, dict) and set(e) == {"name", "question"} for e in labels
        )
        if not shaped or not 1 <= len(labels) <= LABELS_MAX:
            return [f"{path}.labels : attendu de 1 à {LABELS_MAX} étiquettes, chacune {{name, question}}."]
        questions = {f"labels.{e['name']}": e["question"] for e in labels}
        names = [e["name"] for e in labels]
        if bad := [n for n in names if not (isinstance(n, str) and re.fullmatch(NAME, n)) or names.count(n) > 1]:
            return [f"{path}.labels : noms invalides ou en double : {', '.join(map(str, bad))}."]
    errors = []
    for field, question in questions.items():
        errors += text_errors({field: question}, field, 10, 300)
        errors += free_text_errors(f"{path}.{field}", question, "la question porte sur une production.")
    threshold = subagent["threshold"]
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 < threshold < 1:
        errors.append(f"{path}.threshold : attendu une probabilité strictement entre 0 et 1, par exemple 0.7.")
    return [e if e.startswith(path) else f"{path}.{e}" for e in errors]


def list_errors(field: str, items: object, high: int, keys: list[str]) -> list[str]:
    if not isinstance(items, list) or len(items) > high:
        return [f"{field} : attendu une liste de {high} éléments au plus."]
    return [f"{field} : {k!r} apparaît plusieurs fois." for k in sorted({k for k in keys if keys.count(k) > 1})]


def schedule_errors(schedule: object) -> list[str]:
    if isinstance(schedule, dict) and set(schedule) == {"weekdays"}:
        weekdays = schedule["weekdays"]
        if (
            isinstance(weekdays, list)
            and weekdays
            and all(j in WEEKDAYS for j in weekdays)
            and len(set(weekdays)) == len(weekdays)
        ):
            return []
        return [f"schedule.weekdays : attendu une liste sans doublon de jours parmi {', '.join(WEEKDAYS)}."]
    if isinstance(schedule, str) and schedule in SCHEDULES:
        return []
    return [
        f"schedule : {schedule!r} inconnue, attendu weekdays: [monday, thursday] ou l'un de {', '.join(SCHEDULES)}."
    ]


def file_errors(files: object) -> list[str]:
    if not isinstance(files, list) or len(files) > 5:
        return ["files : attendu une liste de 5 noms de fichiers au plus."]
    errors = [
        f"files : {f!r} invalide, attendu minuscules, chiffres, tirets et une extension md, txt, csv ou json."
        for f in files
        if not (isinstance(f, str) and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,40}\.(md|txt|csv|json)", f))
    ]
    return errors + list_errors("files", files, 5, [str(f) for f in files])


def initial_errors(initial_files: dict[str, str], files: object) -> list[str]:
    """What is wrong with the initial values given for an agent's files: undeclared or oversized."""
    declared = files if isinstance(files, list) else []
    return [
        f"fichier initial {name} : pas un fichier déclaré de l'agent, files : {', '.join(map(str, declared)) or 'aucun'}."
        if name not in declared
        else f"fichier initial {name} : {len(content)} caractères, {AGENT_FILE_MAX} au plus."
        for name, content in initial_files.items()
        if name not in declared or len(content) > AGENT_FILE_MAX
    ]


def destination_errors(slug: object, index: int, contact: object, known: dict[str, dict]) -> list[str]:
    path = f"destinations[{index}]"
    if not isinstance(contact, dict) or not {"id", "mode"} <= set(contact) <= {"id", "mode", "grouping"}:
        return [f"{path} : attendu les champs id et mode, et grouping en option."]
    if contact.get("grouping", "single") not in GROUPINGS:
        return [f"{path}.grouping : {contact['grouping']!r} inconnu, attendu {' ou '.join(GROUPINGS)}."]
    destination = known.get(contact["id"])
    if destination is None:
        return [
            f"{path}.id : {contact['id']!r} n'est pas une destination de config/agent_destinations.yaml. "
            f"Un agent ne nomme ni canal ni personne : il choisit une destination de la liste."
            f"{suggestion(contact['id'], list(known))}"
        ]
    if contact["mode"] not in MODES:
        return [f"{path}.mode : {contact['mode']!r} inconnu, modes permis : {', '.join(MODES)}."]
    if contact["mode"] == "autonomous" and slug not in destination["autonomous_allowed"]:
        return [
            f"{path}.mode : le mode autonomous sur {contact['id']!r} n'est pas ouvert à cet agent. "
            "Il s'ouvre par une PR qui l'ajoute à autonomous_allowed dans config/agent_destinations.yaml."
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
    if "title" in doc:
        errors += text_errors(doc, "title", 3, 80)
    if "mission" in doc:
        errors += text_errors(doc, "mission", 20, 400)
        errors += free_text_errors("mission", doc["mission"], "une destination se déclare dans destinations.")
    if "schedule" in doc:
        errors += schedule_errors(doc["schedule"])
    if "files" in doc:
        errors += file_errors(doc["files"])
    if "subagents" in doc:
        subagents = doc["subagents"]
        keys = [json.dumps(o, sort_keys=True, default=str) for o in subagents] if isinstance(subagents, list) else []
        errors += list_errors("subagents", subagents, 5, keys)
        known_models = models()
        errors += [
            e
            for i, o in enumerate(subagents if isinstance(subagents, list) else [])
            for e in subagent_errors(i, o, known_models)
        ]
    if "preparations" in doc:
        steps = doc["preparations"] if isinstance(doc["preparations"], list) else []
        found = [e for i, p in enumerate(steps) for e in agent_connectors.errors(i, p)]
        keys = [] if found else [agent_connectors.label(p) for p in steps]
        errors += list_errors("preparations", doc["preparations"], 5, keys) + found
    if "destinations" in doc:
        contacts = doc["destinations"]
        # Why: an agent that only keeps its own files needs no destination outside Autometa.
        low = 0 if doc.get("files") else 1
        if not isinstance(contacts, list) or not low <= len(contacts) <= 6:
            return [*errors, f"destinations : attendu une liste de {low} à 6 destinations."]
        known = known_destinations()
        for i, contact in enumerate(contacts):
            errors += destination_errors(doc.get("slug"), i, contact, known)
        ids = [c["id"] for c in contacts if isinstance(c, dict) and "id" in c]
        errors += [
            f"destinations : {d!r} apparaît plusieurs fois." for d in sorted({i for i in ids if ids.count(i) > 1})
        ]
    return errors


def describe(doc: dict) -> list[str]:
    """What an accepted configuration does, one line per element, for the review before confirmation."""
    lines = [
        f"destination {c['id']} en mode {c['mode']}"
        + (
            ", un digest par run (productions retenues regroupées par étiquette)"
            if c.get("grouping") == "digest"
            else ""
        )
        for c in doc["destinations"]
    ]
    for i, o in enumerate(doc.get("subagents", []), 1):
        if o["type"] == "classifier" and "labels" in o:
            detail = (
                f"étiquettes {', '.join(e['name'] for e in o['labels'])} au seuil {o['threshold']}, sans rien écarter"
            )
        elif o["type"] == "classifier":
            detail = f"filtre « {o['question']} » au seuil {o['threshold']}"
        elif o["type"] == "extraction":
            detail = f"champs {', '.join(o['schema'])}"
        else:
            detail = f"{o['max_length']} caractères au plus"
        lines.append(f"sous-agent {i} : {o['type']} {o['model']}, {detail}")
    for i, p in enumerate(doc.get("preparations", []), 1):
        main = ("type", "base", "page", "repos", "organization", "url", "dataset", "task")
        options = ", ".join(f"{k} {v}" for k, v in p.items() if k not in main)
        lines.append(f"préparation {i} : {agent_connectors.label(p)}{f' ({options})' if options else ''}")
    lines += [f"fichier de l'agent : {f}, versionné, lisible depuis le chat" for f in doc.get("files", [])]
    lines.append(f"cadence : {cadence(doc.get('schedule'))}")
    return lines


def cadence(schedule: object) -> str:
    weekdays = ", ".join(schedule["weekdays"]) if isinstance(schedule, dict) else None
    return f"chaque {weekdays}" if weekdays else schedule or "à la demande"
