"""Crée le ticket dans le Backlog unifié ; sans --go, montre seulement ce qui serait créé."""

import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import backlog, backlog_creation, backlog_stockage  # noqa: E402
from skills.rediger_ticket.scripts.commun import verifier_configuration  # noqa: E402
from web import config  # noqa: E402

CHAMPS_LISTES = ("equipes", "types")
CHAMPS_TEXTES = ("titre", "corps", "statut")


def chemin_brouillon() -> Path:
    return Path("/tmp/rediger_ticket") / (config.agent_conversation_id() or "local") / "brouillon.json"


def verifier_champs(brouillon: dict) -> None:
    if not isinstance(brouillon, dict):
        raise ValueError("Le brouillon doit être un objet JSON")
    for champ in (*CHAMPS_TEXTES, *CHAMPS_LISTES):
        if not brouillon.get(champ):
            raise ValueError(f"Champ manquant dans le brouillon : {champ}")
    for champ in CHAMPS_LISTES:
        if not isinstance(brouillon[champ], list):
            raise ValueError(f"Le champ {champ} du brouillon doit être une liste")


def ouverture(blocs: list[dict]) -> str:
    """Texte brut du premier paragraphe, le marqueur Autometa compris."""
    premier = next(b for b in blocs if b["type"] == "paragraph")
    return "".join(
        ":autometa:" if t["type"] == "mention" else t["text"]["content"] for t in premier["paragraph"]["rich_text"]
    )


def resoudre(brouillon: dict, contexte: dict, auteur: backlog.Auteur | None) -> backlog_creation.Ticket:
    verifier_champs(brouillon)
    equipes = {e["nom"]: e for e in contexte["equipes"]}
    inconnues = [n for n in brouillon["equipes"] if n not in equipes]
    if inconnues:
        raise ValueError(f"Équipe inconnue : {', '.join(inconnues)}")
    ids = [equipes[n]["id"] for n in brouillon["equipes"]]
    epic = None
    if brouillon.get("epic"):
        epics = {e["nom"]: e["id"] for n in brouillon["equipes"] for e in equipes[n]["epics"]}
        if brouillon["epic"] not in epics:
            raise ValueError(f"Épic inconnu pour ces équipes : {brouillon['epic']}")
        epic = epics[brouillon["epic"]]
    return backlog_creation.Ticket(
        titre=brouillon["titre"],
        corps=brouillon["corps"],
        equipes=ids,
        statut=brouillon["statut"],
        types=brouillon["types"],
        figma=brouillon.get("figma") or None,
        epic=epic,
        champ_auteur=brouillon.get("champ_auteur") or (backlog.champ_auteur(auteur, ids) if auteur else None),
        auteur_notion_id=auteur.notion_id if auteur else None,
        noms={**{equipes[n]["id"]: n for n in brouillon["equipes"]}, **({epic: brouillon["epic"]} if epic else {})},
    )


def run(args: argparse.Namespace) -> str:
    manque = verifier_configuration(annuaire=False)
    if manque:
        raise ValueError(manque)
    chemin = Path(args.brouillon) if args.brouillon else chemin_brouillon()
    brouillon = json.loads(chemin.read_text(encoding="utf-8"))
    email = config.agent_user_email()
    auteur, avis = None, []
    if email:
        try:
            auteur = backlog.trouver_auteur(email)
        except httpx.HTTPError, RuntimeError:
            avis.append("Auteur non inscrit : annuaire ou comptes Notion illisibles.")
    ticket = resoudre(brouillon, backlog_stockage.contexte_courant(), auteur)
    if not args.go:
        if not ticket.auteur_notion_id and not avis:
            avis.append("Auteur non inscrit : pas de compte Notion.")
        charge = backlog_creation.preparer(ticket)
        return "\n".join([
            "Vérification seulement (sans --go) : rien n'est créé.",
            json.dumps(charge["properties"], ensure_ascii=False, indent=2),
            "Noms résolus :",
            json.dumps(ticket.noms, ensure_ascii=False, indent=2),
            f"Corps : {len(charge['children'])} blocs",
            ouverture(charge["children"]),
            *avis,
        ])
    _, url = backlog_creation.creer_ticket(ticket)
    chemin.unlink(missing_ok=True)
    return "\n".join([f"Ticket créé : {url}", *avis])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brouillon", nargs="?", help="fichier JSON du brouillon (défaut : celui de la conversation)")
    parser.add_argument("--go", action="store_true", help="créer vraiment, après l'accord explicite de l'auteur")
    try:
        print(run(parser.parse_args()))
    except (OSError, ValueError) as erreur:
        sys.exit(f"Refusé, rien n'est créé : {erreur}")
    except httpx.HTTPStatusError as erreur:
        if erreur.response.status_code >= 500:
            sys.exit(
                "Notion ne répond pas correctement : vérifier dans Notion si le ticket existe avant de relancer --go."
            )
        sys.exit(f"Notion répond {erreur.response.status_code} : {erreur.response.text[:300]}")
    except httpx.TransportError:
        sys.exit("Notion ne répond pas : vérifier dans Notion si le ticket existe avant de relancer --go.")
    except RuntimeError:
        sys.exit("Notion limite les appels : réessayer dans une minute, après avoir vérifié si le ticket existe.")


if __name__ == "__main__":
    main()
