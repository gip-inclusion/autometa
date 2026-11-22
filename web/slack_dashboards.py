"""Un tableau de bord en Work Object de Slack : son lien interne ou public devient un objet, le même pour les deux."""

import re
from urllib.parse import unquote, urlsplit

from lib import variants
from lib.taxonomy import load_vocabulary
from web import config, cron, publications, slack_entities
from web.database import store
from web.db import get_db
from web.helpers import utcnow

DASHBOARD_PATH = re.compile(r"/(interactive|dashboards)/([a-z0-9_-]{1,100})(?:/.*)?")


def located(url: str) -> tuple[str, bool] | None:
    """Le tableau de bord qu'adresse `url`, et s'il l'est par le site public ; None pour toute autre adresse."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    found = DASHBOARD_PATH.fullmatch(unquote(parts.path))
    host = parts.netloc.lower()
    if found and host and host == urlsplit(config.BASE_URL).netloc.lower():
        return found[2], False
    # Why: une seule application Slack sert toutes les instances ; seule la production répond du site public.
    public = config.ENV.answers_public_dashboard_links and host == urlsplit(config.PUBLIC_DASHBOARDS_PROD_URL).netloc
    if found and found[1] == "dashboards" and public:
        return found[2], True
    return None


def field(key: str, label: str, value, kind: str = "string", **more) -> dict:
    return {"key": key, "label": label, "value": value, "type": kind, **more}


def pane(dashboard: dict, published: dict | None) -> list[dict]:
    """Ce que le volet de détails ajoute au lien interne : produit, actualisation, liens, tags par facette."""
    slug = dashboard["slug"]
    run = cron.get_last_runs(slug).get(slug) if dashboard["has_cron"] else None
    origin = dashboard["conversation_id"] and store.get_conversation(
        dashboard["conversation_id"], include_messages=False
    )
    cadences = {"daily": "Chaque nuit", "weekly": "Chaque semaine", "monthly": "1er du mois"}
    with get_db() as session:
        vocabulary = load_vocabulary(session)
    assigned = [
        (term.facet, term.label) for terms in vocabulary.values() for term in terms if term.name in dashboard["tags"]
    ]
    found = [
        dashboard["website"] and field("product", "Produit", slack_entities.plain(dashboard["website"], 80)),
        dashboard["has_cron"]
        and dashboard["cron_enabled"]
        and field("cadence", "Actualisation", cadences[cron.cadence(dashboard["cron_schedule"])]),
        run
        and run["started_at"]
        and field("last_run", "Dernière actualisation", int(run["started_at"].timestamp()), "slack#/types/timestamp"),
        published and field("public", "Version publique", published["url"].split("://")[-1], link=published["url"]),
        origin
        and field(
            "origin",
            "Conversation d'origine",
            slack_entities.plain(origin.title or "", 150) or "Conversation sans titre",
            link=f"{config.BASE_URL}/c/{origin.id}",
        ),
    ]
    return [*filter(None, found), *slack_entities.tags(assigned, "dashboard", {})]


def entity(url: str, detailed: bool = False) -> dict | None:
    """Le Work Object du tableau de bord qu'adresse `url` ; None s'il est inconnu, ou non publié pour un lien public."""
    slug, public = located(url) or (None, False)
    dashboard = slug and store.get_dashboard(slug)
    if not dashboard:
        return None
    active = publications.list_publications(slug)
    published = next((pub for pub in active if pub["environment"] == "production"), None)
    if public and not published:
        return None
    description = slack_entities.plain(" ".join(dashboard["description"].split()), 300)
    author = dashboard["first_author_email"]
    count = len(variants.list_variants(slug))
    # Why: le site public ne dit d'un tableau que son titre, sa description et sa date de publication.
    fields = {
        "description": {"value": description} if description else None,
        "created_by": {"type": "slack#/types/user", "user": {"text": author.split("@")[0], "email": author}},
        "date_created": {"value": int(dashboard["created_at"].timestamp())},
        "date_updated": {"value": int(dashboard["updated"].timestamp())},
    }
    custom = [
        dashboard["is_archived"] and field("state", "État", "Archivé", tag_color="gray"),
        published and not dashboard["is_archived"] and field("state", "État", "Publié", tag_color="green"),
        # Why: le nombre seul ; un libellé ou un jeton de déclinaison donnerait accès à ce qu'elle montre.
        count and field("variants", "Déclinaisons", count, "integer"),
        *(pane(dashboard, published) if detailed and not public else []),
    ]
    if public:
        fields = {"description": fields["description"]}
        moment = int(published["published_at"].timestamp())
        custom = [field("published", "Publication", moment, "slack#/types/timestamp")]
    return {
        "url": url,
        "external_ref": {"id": slug},
        "entity_type": "slack#/entities/content_item",
        "entity_payload": {
            "attributes": {
                "title": {"text": slack_entities.plain(dashboard["title"], 150)},
                "display_type": "Tableau de bord",
                "product_name": "Autometa",
                # Why: Slack ne remplace un objet que par un plus récent ; un état qui change doit passer.
                "metadata_last_modified": int(utcnow().timestamp()),
            },
            "fields": {name: shown for name, shown in fields.items() if shown},
            "custom_fields": [*filter(None, custom)],
        },
    }
