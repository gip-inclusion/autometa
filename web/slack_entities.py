"""Une conversation en Work Object de Slack : l'objet de son lien collé, et ce que son volet de détails en dit."""

from lib import permalinks
from web import conversation_html, slack_excerpts
from web.helpers import utcnow
from web.stores.records import Conversation


def plain(text: str, limit: int) -> str:
    """Le texte borné où Slack ne lit ni mention ni adresse : une espace sans largeur après « < », « @ » et « : »."""
    return slack_excerpts.inert(slack_excerpts.shortened(text, limit)).replace("://", ":​//")


def details(conv: Conversation) -> list[dict]:
    """Ce que le volet de détails ajoute à l'objet : la première question, le début de la dernière réponse, ses titres."""
    grouped = conversation_html.thread(conversation_html.finished(conv.id, conv.needs_response)[0])
    question = next((parts[0][1] for kind, parts in grouped if kind == "user"), "")
    answers = ("".join(content for _, content in parts) for kind, parts in reversed(grouped) if kind == "assistant")
    answer = slack_excerpts.unfronted(next(answers, ""))
    # Why: seul le début est lu, comme pour un extrait ; une réponse entière occuperait l'analyseur, donc le serveur.
    titles = [anchor.title for anchor in permalinks.anchors(answer[:50_000]) if anchor.kind == "section"][:10]
    found = [
        ("question", "Première question", plain(" ".join(question.split()), 300)),
        ("answer", "Dernière réponse", plain("\n".join(slack_excerpts.read(answer[:4000])[0]), 500)),
        ("sections", "Sections de la réponse", "\n".join(f"• {plain(title, 100)}" for title in titles)),
    ]
    # Why: un champ « string » sans `format` est du texte que Slack ne met pas en forme ; `long` lui donne la largeur.
    return [
        {"key": key, "label": label, "value": value, "type": "string", "long": True}
        for key, label, value in found
        if value
    ]


def entity(url: str, conv: Conversation, more: list[dict] = ()) -> dict:
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
            "custom_fields": [*([running] if conv.needs_response else []), *more],
        },
    }
