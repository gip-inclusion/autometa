"""Dépose la campagne dans la base Notion « Campagnes à valider », ou met à jour sa page ; sans --go, montre seulement."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import httpx

from lib import backlog, notion
from web import config

# Why: les noms des propriétés de la base, en un seul endroit : un renommage dans Notion ne change que cette table.
PROPERTIES = {
    "campagne": "Campagne",
    "statut": "Statut",
    "outil": "Outil",
    "genre": "Genre",
    "cible": "Cible",
    "departements": "Départements",
    "structures": "Structures",
    "contacts": "Contacts",
    "expediteur": "Expéditeur",
    "carte_pdi": "Carte PDI",
    "envoi_souhaite": "Envoi souhaité",
    "demandee_par": "Demandée par",
    "conversation": "Conversation Autometa",
}
# Why: sur un select, l'API Notion crée l'option manquante au lieu de refuser ; les valeurs exactes de la base sont ici.
OUTILS = {"brevo": "Brevo", "lgm": "La Growth Machine"}
GENRES = {"relation": "Relation", "activation": "Activation"}
STATUT = "À valider"
REQUIRED = ("campagne", "outil", "genre", "cible", "expediteur", "corps")
DRAFT_FIELDS = (
    "campagne",
    "cible",
    "departements",
    "structures",
    "contacts",
    "expediteur",
    "carte_pdi",
    "envoi_souhaite",
)


def draft_path(given: str | None) -> Path:
    if given:
        return Path(given)
    conversation = config.agent_conversation_id()
    if not conversation:
        raise ValueError("AUTOMETA_CONVERSATION_ID absent : donner le chemin du brouillon")
    return config.WORKDIR_ROOT / conversation / "campagne.json"


def property_value(schema: dict, field: str, raw) -> dict:
    """Valeur Notion d'un champ du brouillon, selon le type que la base donne à sa propriété."""
    name = PROPERTIES[field]
    if name not in schema:
        raise ValueError(f"Propriété absente de la base : « {name} »")
    kind = schema[name]["type"]
    match kind:
        case "title" | "rich_text":
            text = ", ".join(map(str, raw)) if isinstance(raw, list) else str(raw)
            return {kind: [{"text": {"content": text}}]}
        case "select" | "status":
            options = [option["name"] for option in schema[name][kind]["options"]]
            if raw not in options:
                raise ValueError(f"« {raw} » n'est pas une option de « {name} » ({', '.join(options)})")
            return {kind: {"name": raw}}
        case "multi_select":
            return {kind: [{"name": str(item)} for item in (raw if isinstance(raw, list) else [raw])]}
        case "number" | "url":
            return {kind: raw}
        case "date":
            return {kind: {"start": date.fromisoformat(raw).isoformat()}}
        case "people":
            return {kind: [{"id": raw}]}
    raise ValueError(f"Type de propriété non pris en charge pour « {name} » : {kind}")


def requester() -> tuple[str | None, str | None]:
    """Compte Notion de la personne qui fait la demande, ou la raison de son absence."""
    email = config.agent_user_email()
    if not email:
        return None, "Demandée par : personne connectée inconnue, propriété laissée vide."
    try:
        account = backlog.notion_user(email)
    except httpx.HTTPError, notion.NotionRateLimitError:
        return None, "Demandée par : comptes Notion illisibles, propriété laissée vide."
    if account is None:
        return None, "Demandée par : pas de compte Notion pour cette personne, propriété laissée vide."
    return account[0], None


def fields(draft: dict) -> tuple[dict, list[str]]:
    """Champs à écrire, valeurs exactes de la base comprises, et ce qui reste vide."""
    if not isinstance(draft, dict):
        raise ValueError("Le brouillon doit être un objet JSON")
    missing = [f for f in REQUIRED if not draft.get(f)]
    if missing:
        raise ValueError(f"Champ manquant dans le brouillon : {', '.join(missing)}")
    if draft["outil"] not in OUTILS:
        raise ValueError(f"Outil inconnu : {draft['outil']} (brevo ou lgm)")
    if draft["genre"] not in GENRES:
        raise ValueError(f"Genre inconnu : {draft['genre']} (relation ou activation)")
    values = {f: draft[f] for f in DRAFT_FIELDS if draft.get(f) not in (None, "", [])}
    values |= {"statut": STATUT, "outil": OUTILS[draft["outil"]], "genre": GENRES[draft["genre"]]}
    warnings = []
    conversation = config.agent_conversation_id()
    if config.BASE_URL and conversation:
        values["conversation"] = f"{config.BASE_URL}/explorations/{conversation}"
    else:
        warnings.append("Conversation Autometa : adresse de l'application inconnue, propriété laissée vide.")
    account, reason = requester()
    if account:
        values["demandee_par"] = account
    else:
        warnings.append(reason)
    return values, warnings


def run(args: argparse.Namespace) -> str:
    database = config.NOTION_CAMPAIGNS_DB
    if not database:
        raise ValueError("NOTION_CAMPAIGNS_DB absent : la base « Campagnes à valider » n'est pas configurée ici")
    path = draft_path(args.draft)
    draft = json.loads(path.read_text(encoding="utf-8"))
    values, warnings = fields(draft)
    schema = notion.notion_request("GET", f"databases/{database}")["properties"]
    properties = {PROPERTIES[f]: property_value(schema, f, raw) for f, raw in values.items()}
    page = draft.get("page")
    if not args.go:
        action = f"mise à jour de {page}" if page else "création d'une page"
        return "\n".join([
            f"Vérification seulement (sans --go), {action} : rien n'est écrit.",
            json.dumps(properties, ensure_ascii=False, indent=2),
            *warnings,
        ])
    if page:
        page_id = notion.db_id_from_url(page)
        notion.notion_request("PATCH", f"pages/{page_id}", {"properties": properties})
        notion.replace_content(page_id, draft["corps"])
        return "\n".join([f"Page mise à jour : {page}", *warnings])
    created = notion.notion_request("POST", "pages", {"parent": {"database_id": database}, "properties": properties})
    # Why: l'adresse est gardée avant le corps : si l'ajout du corps échoue, la relance met à jour cette page.
    draft["page"] = created["url"]
    path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    notion.append_markdown(created["id"], draft["corps"])
    return "\n".join([f"Page créée : {created['url']}", *warnings])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", nargs="?", help="fichier JSON de la campagne (défaut : celui de la conversation)")
    parser.add_argument("--go", action="store_true", help="écrire vraiment, après l'accord du bizdev")
    try:
        print(run(parser.parse_args()))
    except (OSError, ValueError) as error:
        sys.exit(f"Refusé, rien n'est écrit : {error}")
    except httpx.HTTPStatusError as error:
        sys.exit(f"Notion répond {error.response.status_code} : {error.response.text[:300]}")
    except httpx.TransportError:
        sys.exit("Notion ne répond pas : vérifier dans Notion si la page existe avant de relancer --go.")
    except notion.NotionRateLimitError:
        sys.exit("Notion limite les appels : réessayer dans une minute, après avoir vérifié si la page existe.")


if __name__ == "__main__":
    main()
