"""Agent configuration, format pdi.agent/1: strict YAML reading and validation against the closed destination list."""

import difflib
import json
import logging
import re

import yaml

from lib import agent_connectors
from web import config

logger = logging.getLogger(__name__)

__all__ = [
    "CADENCES",
    "CHAMP_TYPES",
    "FICHIER_MAX",
    "FORMAT",
    "JOURS",
    "MODES",
    "describe",
    "destinations",
    "initial_errors",
    "modeles",
    "parse",
    "target_gaps",
    "validate",
    "warn_target_gaps",
]

FORMAT = "pdi.agent/1"
MODES = ("ombre", "relecture", "reel")
REGROUPEMENTS = ("unitaire", "digest")
FIELDS = ("format", "slug", "titre", "mission", "points_de_contact")
OPTIONAL_FIELDS = ("cadence", "outils_modeles", "preparations", "fichiers")
CADENCES = {"quotidienne": "daily", "hebdomadaire": "weekly", "mensuelle": "monthly"}
JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
FICHIER_MAX = 100_000
# Why: what an extraction may declare, flat on purpose; each maps to its JSON Schema type for Ollama.
CHAMP_TYPES = {"texte": "string", "nombre": "number", "entier": "integer", "booleen": "boolean"}
# Why: the type-specific fields of a sub-agent, besides type and modele.
SUBAGENT_FIELDS = {
    "classificateur": (("question", "seuil"), ("etiquettes", "seuil")),
    "extraction": (("schema",),),
    "resume": (("longueur_max",),),
}
# Why: clef answers up to 64 questions in one call; ten labels keep one production's verdict readable.
ETIQUETTES_MAX = 10
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


def read_config(name: str) -> dict:
    return yaml.safe_load((config.BASE_DIR / "config" / f"agent_{name}.yaml").read_text())


def closed_list(name: str) -> dict[str, dict]:
    return {d["id"]: d for d in read_config(name)[name]}


def destinations() -> dict[str, dict]:
    """The closed list of destinations, by id."""
    return closed_list("destinations")


def modeles() -> dict[str, list[str]]:
    """The closed list of sub-agent types, each with the Ollama Cloud models it may use."""
    return {t["type"]: t["modeles"] for t in read_config("modeles")["types"]}


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
    kind, variants = outil["type"], SUBAGENT_FIELDS[outil["type"]]
    if set(outil) not in [{"type", "modele", *fields} for fields in variants]:
        shapes = " ou ".join("type, modele, " + ", ".join(fields) for fields in variants)
        return [f"{path} : un sous-agent {kind} a exactement les champs {shapes}."]
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
    if "question" in outil:
        questions = {"question": outil["question"]}
    else:
        labels = outil["etiquettes"]
        shaped = isinstance(labels, list) and all(isinstance(e, dict) and set(e) == {"nom", "question"} for e in labels)
        if not shaped or not 1 <= len(labels) <= ETIQUETTES_MAX:
            return [f"{path}.etiquettes : attendu de 1 à {ETIQUETTES_MAX} étiquettes, chacune {{nom, question}}."]
        questions = {f"etiquettes.{e['nom']}": e["question"] for e in labels}
        names = [e["nom"] for e in labels]
        if bad := [n for n in names if not (isinstance(n, str) and re.fullmatch(NAME, n)) or names.count(n) > 1]:
            return [f"{path}.etiquettes : noms invalides ou en double : {', '.join(map(str, bad))}."]
    errors = []
    for field, question in questions.items():
        errors += text_errors({field: question}, field, 10, 300)
        errors += free_text_errors(f"{path}.{field}", question, "la question porte sur une production.")
    seuil = outil["seuil"]
    if isinstance(seuil, bool) or not isinstance(seuil, (int, float)) or not 0 < seuil < 1:
        errors.append(f"{path}.seuil : attendu une probabilité strictement entre 0 et 1, par exemple 0.7.")
    return [e if e.startswith(path) else f"{path}.{e}" for e in errors]


def list_errors(field: str, items: object, high: int, keys: list[str]) -> list[str]:
    if not isinstance(items, list) or len(items) > high:
        return [f"{field} : attendu une liste de {high} éléments au plus."]
    return [f"{field} : {k!r} apparaît plusieurs fois." for k in sorted({k for k in keys if keys.count(k) > 1})]


def cadence_errors(cadence: object) -> list[str]:
    if isinstance(cadence, dict) and set(cadence) == {"jours"}:
        jours = cadence["jours"]
        if isinstance(jours, list) and jours and all(j in JOURS for j in jours) and len(set(jours)) == len(jours):
            return []
        return [f"cadence.jours : attendu une liste sans doublon de jours parmi {', '.join(JOURS)}."]
    if isinstance(cadence, str) and cadence in CADENCES:
        return []
    return [f"cadence : {cadence!r} inconnue, attendu jours: [lundi, jeudi] ou l'un de {', '.join(CADENCES)}."]


def fichier_errors(fichiers: object) -> list[str]:
    if not isinstance(fichiers, list) or len(fichiers) > 5:
        return ["fichiers : attendu une liste de 5 noms de fichiers au plus."]
    errors = [
        f"fichiers : {f!r} invalide, attendu minuscules, chiffres, tirets et une extension md, txt, csv ou json."
        for f in fichiers
        if not (isinstance(f, str) and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,40}\.(md|txt|csv|json)", f))
    ]
    return errors + list_errors("fichiers", fichiers, 5, [str(f) for f in fichiers])


def initial_errors(initiaux: dict[str, str], fichiers: object) -> list[str]:
    """What is wrong with the initial values given for an agent's files: undeclared or oversized."""
    declared = fichiers if isinstance(fichiers, list) else []
    return [
        f"fichier initial {nom} : pas un fichier déclaré de l'agent, fichiers : {', '.join(map(str, declared)) or 'aucun'}."
        if nom not in declared
        else f"fichier initial {nom} : {len(contenu)} caractères, {FICHIER_MAX} au plus."
        for nom, contenu in initiaux.items()
        if nom not in declared or len(contenu) > FICHIER_MAX
    ]


def contact_errors(slug: object, index: int, contact: object, known: dict[str, dict]) -> list[str]:
    path = f"points_de_contact[{index}]"
    if not isinstance(contact, dict) or not {"id", "mode"} <= set(contact) <= {"id", "mode", "regroupement"}:
        return [f"{path} : attendu les champs id et mode, et regroupement en option."]
    if contact.get("regroupement", "unitaire") not in REGROUPEMENTS:
        return [f"{path}.regroupement : {contact['regroupement']!r} inconnu, attendu {' ou '.join(REGROUPEMENTS)}."]
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
    if "cadence" in doc:
        errors += cadence_errors(doc["cadence"])
    if "fichiers" in doc:
        errors += fichier_errors(doc["fichiers"])
    if "outils_modeles" in doc:
        outils = doc["outils_modeles"]
        keys = [json.dumps(o, sort_keys=True, default=str) for o in outils] if isinstance(outils, list) else []
        errors += list_errors("outils_modeles", outils, 5, keys)
        known_models = modeles()
        errors += [
            e
            for i, o in enumerate(outils if isinstance(outils, list) else [])
            for e in outil_errors(i, o, known_models)
        ]
    if "preparations" in doc:
        steps = doc["preparations"] if isinstance(doc["preparations"], list) else []
        found = [e for i, p in enumerate(steps) for e in agent_connectors.errors(i, p)]
        keys = [] if found else [agent_connectors.label(p) for p in steps]
        errors += list_errors("preparations", doc["preparations"], 5, keys) + found
    if "points_de_contact" in doc:
        contacts = doc["points_de_contact"]
        # Why: an agent that only keeps its own files needs no destination outside Autometa.
        low = 0 if doc.get("fichiers") else 1
        if not isinstance(contacts, list) or not low <= len(contacts) <= 6:
            return [*errors, f"points_de_contact : attendu une liste de {low} à 6 destinations."]
        known = destinations()
        for i, contact in enumerate(contacts):
            errors += contact_errors(doc.get("slug"), i, contact, known)
        ids = [c["id"] for c in contacts if isinstance(c, dict) and "id" in c]
        errors += [
            f"points_de_contact : {d!r} apparaît plusieurs fois." for d in sorted({i for i in ids if ids.count(i) > 1})
        ]
    return errors


def describe(doc: dict) -> list[str]:
    """What an accepted configuration does, one line per element, for the review before confirmation."""
    lines = [
        f"destination {c['id']} en mode {c['mode']}"
        + (
            ", un digest par run (productions retenues regroupées par étiquette)"
            if c.get("regroupement") == "digest"
            else ""
        )
        for c in doc["points_de_contact"]
    ]
    for i, o in enumerate(doc.get("outils_modeles", []), 1):
        if o["type"] == "classificateur" and "etiquettes" in o:
            detail = (
                f"étiquettes {', '.join(e['nom'] for e in o['etiquettes'])} au seuil {o['seuil']}, sans rien écarter"
            )
        elif o["type"] == "classificateur":
            detail = f"filtre « {o['question']} » au seuil {o['seuil']}"
        elif o["type"] == "extraction":
            detail = f"champs {', '.join(o['schema'])}"
        else:
            detail = f"{o['longueur_max']} caractères au plus"
        lines.append(f"sous-agent {i} : {o['type']} {o['modele']}, {detail}")
    for i, p in enumerate(doc.get("preparations", []), 1):
        main = ("type", "base", "page", "depots", "organisation", "url", "jeu", "tache")
        options = ", ".join(f"{k} {v}" for k, v in p.items() if k not in main)
        lines.append(f"préparation {i} : {agent_connectors.label(p)}{f' ({options})' if options else ''}")
    lines += [f"fichier de l'agent : {f}, versionné, lisible depuis le chat" for f in doc.get("fichiers", [])]
    cadence = doc.get("cadence")
    jours = ", ".join(cadence["jours"]) if isinstance(cadence, dict) else None
    lines.append(f"cadence : {f'chaque {jours}' if jours else cadence or 'à la demande'}")
    return lines
