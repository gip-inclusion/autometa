"""Zendesk macros: read them by category and in plain words, plan reviewable edits through zendesk_changeset."""

import re
from collections.abc import Callable
from typing import Any, Optional

from . import zendesk_changeset as cs
from .zendesk import Macro, ZendeskAPI

__all__ = ["category", "by_category", "describe", "plan", "replace", "replace_tag", "export"]

NO_CATEGORY = "Sans catégorie"
TEXT_FIELDS = ("subject", "comment_value", "comment_value_html")
# Why: Zendesk's editor stores what an agent sees as a space or a quote under several encodings.
DISPLAYED_AS = {
    " ": (" ", "\xa0", "&nbsp;", "&#160;"),
    '"': ('"', "&quot;", "&#34;"),
    "'": ("'", "&#39;", "&apos;"),
    "&": ("&", "&amp;"),
    "<": ("<", "&lt;"),
    ">": (">", "&gt;"),
}
STATUSES = {
    "new": "Nouveau",
    "open": "Ouvert",
    "pending": "En attente",
    "hold": "En pause",
    "solved": "Résolu",
    "closed": "Clos",
}
SPECIAL_VALUES = {"current_user": "l'agent qui applique la macro", "": "personne"}
LABELS = {
    "status": "Statut",
    "custom_status_id": "Statut personnalisé",
    "assignee_id": "Assigné à",
    "group_id": "Groupe",
    "brand_id": "Marque",
    "ticket_form_id": "Formulaire",
    "set_tags": "Étiquettes (remplacent toutes les autres)",
    "current_tags": "Étiquettes ajoutées",
    "remove_tags": "Étiquettes retirées",
    "subject": "Sujet",
    "priority": "Priorité",
    "type": "Type",
    "comment_mode_is_public": "Réponse publique",
    "comment_value": "Réponse",
    "comment_value_html": "Réponse",
}
REFERENCES = {
    "custom_status_id": ("custom_statuses", "agent_label"),
    "assignee_id": ("users", "name"),
    "group_id": ("groups", "name"),
    "brand_id": ("brands", "name"),
    "ticket_form_id": ("ticket_forms", "name"),
}


def category(title: str) -> Optional[str]:
    """First segment of a `A::B::C` title, None when the title has no category."""
    head, separator, _ = title.partition("::")
    return head.strip() if separator else None


def by_category(macros: list[Macro]) -> dict[str, list[Macro]]:
    """Macros grouped by category, categories in alphabetical order and uncategorised ones last."""
    groups: dict[str, list[Macro]] = {}
    for macro in macros:
        groups.setdefault(category(macro.title) or NO_CATEGORY, []).append(macro)
    return dict(sorted(groups.items(), key=lambda kv: (kv[0] == NO_CATEGORY, kv[0].casefold())))


def name_of(api: ZendeskAPI, resource: str, key: str, item_id: Any) -> str:
    item = api.lookup(resource, item_id)
    return item[key] if item else f"inconnu (#{item_id})"


def describe_action(api: ZendeskAPI, action: dict) -> dict:
    field, value = action["field"], action["value"]
    if field.startswith("custom_fields_"):
        field_id = field.removeprefix("custom_fields_")
        ticket_field = api.lookup("ticket_fields", field_id)
        if not ticket_field:
            return {"label": f"Champ inconnu (#{field_id})", "value": value}
        options = {o["value"]: o["name"] for o in ticket_field.get("custom_field_options", [])}
        return {"label": ticket_field["title"], "value": options.get(value, value)}
    label = LABELS.get(field, field)
    if field == "status":
        return {"label": label, "value": STATUSES.get(value, value)}
    if field == "comment_mode_is_public":
        return {"label": label, "value": "oui" if value == "true" else "non"}
    if field in REFERENCES and value in SPECIAL_VALUES:
        return {"label": label, "value": SPECIAL_VALUES[value]}
    if field in REFERENCES:
        return {"label": label, "value": name_of(api, *REFERENCES[field], value)}
    return {"label": label, "value": value}


def describe(api: ZendeskAPI, macro: Macro) -> dict:
    """A macro in plain words: statuses, groups, agents and ticket fields by name, deleted ones as « inconnu »."""
    restriction = macro.restriction
    restricted_to = None
    if restriction and restriction["type"] == "Group":
        restricted_to = [name_of(api, "groups", "name", i) for i in restriction.get("ids") or [restriction["id"]]]
    elif restriction:
        restricted_to = [name_of(api, "users", "name", restriction["id"])]
    return {
        "id": macro.id,
        "title": macro.title,
        "html_url": macro.html_url,
        "category": category(macro.title),
        "active": macro.active,
        "description": macro.description,
        "usage_30d": macro.usage_30d,
        "restricted_to": restricted_to,
        "actions": [describe_action(api, a) for a in macro.actions],
    }


def plan(
    macros: list[Macro], transform: Callable[[dict], dict], label: str, params: Optional[dict] = None, **notes: Any
) -> Optional[dict]:
    """Changeset over macros; transform maps {title, description, active, actions} to its new value."""
    return cs.plan_items("macros", macros, transform, label, params, **notes)


def as_displayed(pattern: str) -> str:
    """Regex matching the literal pattern however Zendesk encoded its spaces, quotes and brackets."""
    return "".join(
        f"(?:{'|'.join(map(re.escape, DISPLAYED_AS[c]))})" if c in DISPLAYED_AS else re.escape(c) for c in pattern
    )


def replace(
    api: ZendeskAPI,
    pattern: str,
    replacement: str,
    regex: bool = False,
    include_markup: bool = False,
    macros: Optional[list[Macro]] = None,
    label: Optional[str] = None,
) -> Optional[dict]:
    """Plan a search-and-replace over titles, descriptions, subjects and the visible text of replies."""
    if not pattern:
        raise ValueError("texte cherché vide")
    compiled = re.compile(pattern if regex else as_displayed(pattern))
    sub = replacement if regex else replacement.replace("\\", r"\\")
    protected = cs.MARKUP + r"|\{\{.*?\}\}|\{%.*?%\}"

    def replace_text(text: str) -> str:
        segments = cs.split_markup(text, protected)
        return "".join(
            compiled.sub(sub, seg) if include_markup or i % 2 == 0 else seg for i, seg in enumerate(segments)
        )

    def transform(fields: dict) -> dict:
        actions = [
            {**a, "value": replace_text(a["value"])} if a["field"] in TEXT_FIELDS else a for a in fields["actions"]
        ]
        return {
            **fields,
            "title": replace_text(fields["title"]),
            "description": replace_text(fields["description"]),
            "actions": actions,
        }

    def protected_hits(macro: Macro) -> int:
        texts = [a["value"] for a in macro.actions if a["field"] in TEXT_FIELDS] + [macro.title, macro.description]
        return sum(len(compiled.findall(seg)) for text in texts for seg in cs.split_markup(text, protected)[1::2])

    if macros is None:
        macros = api.list_macros()
    markup_hits = {m.id: hits for m in macros if (hits := protected_hits(m))}
    params = {"pattern": pattern, "replacement": replacement, "regex": regex, "include_markup": include_markup}
    return plan(macros, transform, label or f"remplacer {pattern}", params, markup_hits=markup_hits)


def replace_tag(
    api: ZendeskAPI, tag: str, replacement: str, macros: Optional[list[Macro]] = None, label: Optional[str] = None
) -> Optional[dict]:
    """Plan swapping one whole tag for another wherever a macro adds, sets or removes it, without duplicates."""
    if not tag or not replacement or " " in tag + replacement:
        raise ValueError("étiquette vide ou contenant une espace")

    def swap(value: str) -> str:
        tags = value.split()
        if tag not in tags:
            return value
        return " ".join(dict.fromkeys(replacement if t == tag else t for t in tags))

    def transform(fields: dict) -> dict:
        actions = [{**a, "value": swap(a["value"])} if a["field"].endswith("_tags") else a for a in fields["actions"]]
        return {**fields, "actions": actions}

    if macros is None:
        macros = api.list_macros()
    params = {"tag": tag, "replacement": replacement}
    return plan(macros, transform, label or f"remplacer l'étiquette {tag}", params)


def export(api: ZendeskAPI) -> dict:
    """Dump every macro's raw payload, actions included, to S3; returns path, count and a presigned URL."""
    return cs.export("macros", [m.raw for m in api.list_macros()])
