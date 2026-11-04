"""Agent configuration, format pdi.agent/1: strict YAML reading and validation against the closed destination list."""

import difflib
import logging
import re

import yaml

from web import config

logger = logging.getLogger(__name__)

__all__ = ["FORMAT", "MODES", "destinations", "parse", "target_gaps", "validate", "warn_target_gaps"]

FORMAT = "pdi.agent/1"
MODES = ("ombre", "relecture", "reel")
FIELDS = ("format", "slug", "titre", "mission", "points_de_contact")
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


def destinations() -> dict[str, dict]:
    """The closed list of destinations, by id."""
    raw = yaml.safe_load((config.BASE_DIR / "config" / "agent_destinations.yaml").read_text())
    return {d["id"]: d for d in raw["destinations"]}


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
    errors = [f"{k} : champ obligatoire absent." for k in FIELDS if k not in doc]
    errors += [
        f"{k} : champ inconnu, le format est fermé.{suggestion(k, list(FIELDS))}" for k in doc if k not in FIELDS
    ]
    if "format" in doc and doc["format"] != FORMAT:
        errors.append(f"format : doit valoir {FORMAT!r}.")
    if "slug" in doc and not (isinstance(doc["slug"], str) and re.fullmatch(r"[a-z][a-z0-9-]{2,40}", doc["slug"])):
        errors.append("slug : minuscules, chiffres et tirets, de 3 à 41 caractères, commençant par une lettre.")
    if "titre" in doc:
        errors += text_errors(doc, "titre", 3, 80)
    if "mission" in doc:
        errors += text_errors(doc, "mission", 20, 400)
        if isinstance(doc["mission"], str) and (found := FORBIDDEN_FREE_TEXT.search(doc["mission"])):
            errors.append(
                f"mission : contient {found.group(0)!r}. Ni lien, ni personne, ni canal dans la mission : "
                "une destination se déclare dans points_de_contact."
            )
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
