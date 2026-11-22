"""Une conversation en Work Object de Slack : son lien collé devient un objet, avec titre, auteur, dates et état."""

from web import slack_excerpts
from web.helpers import utcnow
from web.stores.records import Conversation


def plain(text: str, limit: int) -> str:
    """Le texte borné où Slack ne lit ni mention ni adresse : une espace sans largeur après « < », « @ » et « : »."""
    return slack_excerpts.inert(slack_excerpts.shortened(text, limit)).replace("://", ":​//")


def entity(url: str, conv: Conversation) -> dict:
    """Le Work Object d'une conversation : un « content item », le même quelle que soit l'adresse qui y mène."""
    fields = {
        "created_by": (
            {"type": "slack#/types/user", "user": {"text": conv.user_id.split("@")[0], "email": conv.user_id}}
            if conv.user_id
            else None
        ),
        "date_created": {"value": int(conv.created_at.timestamp())},
        "date_updated": {"value": int(conv.updated_at.timestamp())},
    }
    running = {"key": "state", "label": "État", "value": "En cours", "type": "string", "tag_color": "blue"}
    return {
        "url": url,
        "external_ref": {"id": conv.id},
        "entity_type": "slack#/entities/content_item",
        "entity_payload": {
            "attributes": {
                "title": {"text": plain(conv.title or "", 150) or "Conversation sans titre"},
                "display_type": "Conversation",
                "product_name": "Autometa",
                # Why: Slack ne remplace un objet que par un plus récent ; un état qui change doit passer.
                "metadata_last_modified": int(utcnow().timestamp()),
            },
            "fields": {name: field for name, field in fields.items() if field},
            "custom_fields": [running] if conv.needs_response else [],
        },
    }
