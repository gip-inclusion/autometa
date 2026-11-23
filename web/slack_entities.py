"""Une conversation en Work Object de Slack : l'objet de son lien collé, et ce que son volet de détails en dit."""

from lib import permalinks
from lib.answer_html import ANSWER
from lib.taxonomy import ordered_facets
from web import conversation_html, slack_excerpts
from web.database import store
from web.helpers import to_local, utcnow
from web.search_filters import SEARCH_FACET_LABELS
from web.stores.records import Conversation


def plain(text: str, limit: int) -> str:
    """Le texte borné où Slack ne lit ni mention ni adresse : une espace sans largeur après « < », « @ » et « : »."""
    return slack_excerpts.inert(slack_excerpts.shortened(text, limit)).replace("://", ":​//")


MONTHS = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc.")


def day(moment) -> str:
    local = to_local(moment)
    return f"{local.day}{'er' if local.day == 1 else ''} {MONTHS[local.month - 1]} {local.year}"


def dates(created, updated, made: str = "Créé") -> dict:
    """La création et la dernière modification d'un objet en un seul champ lisible ; un seul jour s'il est le même."""
    said = f"{made} le {day(created)}"
    if day(updated) != day(created):
        said += f", modifié{made[4:]} le {day(updated)}"
    return {"key": "dates", "label": "Dates", "value": said, "type": "string"}


def author(email: str) -> dict:
    """L'auteur d'un objet : le nom que porte son adresse, que Slack rapproche d'un compte par elle."""
    return {"type": "slack#/types/user", "user": {"text": plain(email.split("@")[0], 80), "email": email}}


def details(conv: Conversation) -> list[dict]:
    """Ce que le volet de détails ajoute à l'objet : sa première question, sa dernière réponse, ses titres, ses tags."""
    grouped = conversation_html.grouping(conversation_html.finished(conv.id, conv.needs_response)[0])[0]
    question = next((parts[0][1] for kind, parts in grouped if kind == "user"), "")
    answers = ("".join(content for _, content in parts) for kind, parts in reversed(grouped) if kind == "assistant")
    answer = slack_excerpts.unfronted(next(answers, ""))
    # Why: seul le début est lu, comme pour un extrait ; une réponse entière occuperait l'analyseur, donc le serveur.
    sections = [anchor for anchor in permalinks.anchors(answer[:50_000]) if anchor.kind == "section"][:10]
    titles = [slack_excerpts.inline_text(ANSWER.parseInline(section.title[:500])[0]) for section in sections]
    found = [
        ("question", "Première question", plain(" ".join(question.split()), 300)),
        ("answer", "Dernière réponse", plain("\n".join(slack_excerpts.read(answer[:4000])[0]), 500)),
        ("sections", "Sections de la réponse", "\n".join(f"• {plain(title, 100)}" for title in titles)),
    ]
    # Why: un champ « string » sans `format` est du texte que Slack ne met pas en forme ; `long` lui donne la largeur.
    texts = [
        {"key": key, "label": label, "value": value, "type": "string", "long": True}
        for key, label, value in found
        if value
    ]
    assigned = [(tag.type, tag.label) for tag in store.get_conversation_tags(conv.id)]
    return texts + tags(assigned, "conversation", SEARCH_FACET_LABELS)


def tags(assigned: list[tuple[str, str]], object_type: str, renamed: dict[str, str]) -> list[dict]:
    """Les tags d'un objet (facette, libellé), un champ par facette dans l'ordre de l'interface ; aucun sans tag."""
    return [
        {
            "key": f"tags_{facet.name}",
            "label": renamed.get(facet.name, facet.label),
            "type": "array",
            "item_type": "string",
            "value": [{"value": plain(label, 80)} for name, label in assigned if name == facet.name],
        }
        for facet in ordered_facets(object_type)
        if any(name == facet.name for name, _ in assigned)
    ]


def entity(url: str, conv: Conversation, more: list[dict] = ()) -> dict:
    """Le Work Object d'une conversation : un « content item », le même quelle que soit l'adresse qui y mène."""
    fields = {
        "created_by": author(conv.user_id) if conv.user_id else None,
    }
    running = {"key": "state", "label": "État", "value": "En cours", "type": "string", "tag_color": "blue"}
    return {
        "url": url,
        # Why: Slack rassemble sous une même référence les conversations où un objet est partagé ; le type sépare
        # les identifiants de conversations de ceux des tableaux de bord.
        "external_ref": {"id": conv.id, "type": "conversation"},
        "entity_type": "slack#/entities/content_item",
        "entity_payload": {
            "attributes": {
                "title": {"text": plain(conv.title or "", 150) or "Conversation sans titre"},
                "display_type": "Conversation",
                "product_name": "Autometa",
                # Why: Slack rafraîchit la carte d'un objet dès qu'il en reçoit un plus récent, volet ouvert compris ;
                # seul un tour en cours, dont l'état va changer, date l'objet de maintenant.
                "metadata_last_modified": int((utcnow() if conv.needs_response else conv.updated_at).timestamp()),
            },
            "fields": {name: field for name, field in fields.items() if field},
            "custom_fields": [
                dates(conv.created_at, conv.updated_at, "Créée"),
                *([running] if conv.needs_response else []),
                *more,
            ],
        },
    }
