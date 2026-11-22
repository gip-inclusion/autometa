"""Une conversation en Work Object de Slack, à l'essai : le lien collé devient un objet avec titre, auteur et extrait."""

from urllib.parse import unquote, urlsplit

from web import slack_charts, slack_excerpts
from web.helpers import utcnow
from web.stores.records import Conversation


def described(excerpt: list[dict]) -> str:
    """L'extrait en un texte : ses paragraphes, son tableau ligne à ligne, son graphique nommé."""
    lines = []
    for block in excerpt:
        if block["type"] == "table_excerpt":
            table = block["native"][0]
            lines += [" | ".join(cell["text"] for cell in row) for row in table["rows"][:11]]
            lines += [note["elements"][0]["text"] for note in block["native"][1:]]
        elif block["type"] == "chart":
            lines.append(f"Graphique : {block['title']}" if block["title"] else "Graphique")
        else:
            lines.append(block["text"]["text"])
    return slack_excerpts.inert("\n".join(lines))


def entity(url: str, conv: Conversation, excerpt: list[dict]) -> dict:
    """Le Work Object d'une adresse de conversation : un « content item » que Slack montre à la place de la carte."""
    chart = next((block for block in excerpt if block["type"] == "chart"), None)
    image = chart and slack_charts.files.get(slack_charts.key(chart["source"]))
    description = described(excerpt)
    fields = {
        "description": {"value": description} if description else None,
        "created_by": (
            {"type": "slack#/types/user", "user": {"text": conv.user_id.split("@")[0], "email": conv.user_id}}
            if conv.user_id
            else None
        ),
        "date_created": {"value": int(conv.created_at.timestamp())},
        "date_updated": {"value": int(conv.updated_at.timestamp())},
        "preview": (
            {"type": "slack#/types/image", "slack_file": {"id": image}, "alt_text": chart["title"] or "Graphique"}
            if image
            else None
        ),
    }
    running = {"key": "etat", "label": "État", "value": "En cours", "type": "string", "tag_color": "blue"}
    return {
        "app_unfurl_url": url,
        "url": url,
        # Why: un extrait par adresse ; sous un même identifiant, Slack tiendrait deux permaliens pour un seul objet.
        "external_ref": {"id": unquote(urlsplit(url).path)},
        "entity_type": "slack#/entities/content_item",
        "entity_payload": {
            "attributes": {
                "title": {
                    "text": slack_excerpts.inert(slack_excerpts.shortened(conv.title or "", 150))
                    or "Conversation sans titre"
                },
                "display_type": "Conversation",
                "product_name": "Autometa",
                # Why: Slack ne remplace un objet que par un plus récent ; l'image qui arrive après coup doit passer.
                "metadata_last_modified": int(utcnow().timestamp()),
            },
            "fields": {name: field for name, field in fields.items() if field},
            "custom_fields": [running] if conv.needs_response else [],
        },
    }
