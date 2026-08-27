"""Facettes de tags et accès au vocabulaire — source unique pour le seed, la validation et le prompt."""

import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from web.models import Tag, TagImplication

__all__ = [
    "FACETS",
    "FACETS_BY_NAME",
    "FACET_PRIORITY",
    "Facet",
    "Term",
    "apply_toggle",
    "build_prompt_taxonomy",
    "expand_implications",
    "invert_implications",
    "load_implications",
    "load_vocabulary",
    "normalize_tag_name",
    "normalize_tags",
    "ordered_facets",
]


@dataclass(frozen=True)
class Facet:
    name: str
    label: str
    max_terms: int | None
    # Why: seules les facettes qui suivent le produit ou le terrain bougent assez vite pour
    # justifier une création en libre-service ; usage/mesure/source restent éditoriales.
    user_extensible: bool = False


@dataclass(frozen=True)
class Term:
    name: str
    label: str
    facet: str
    description: str | None = None
    pending: bool = False


FACETS = (
    Facet("usage", "Usage", 1),
    Facet("feature", "Fonctionnalité", None, user_extensible=True),
    Facet("audience", "Public", None, user_extensible=True),
    Facet("theme", "Thème", 2, user_extensible=True),
    Facet("mesure", "Mesure", 2),
    Facet("source", "Source", None),
    Facet("territoire", "Territoire", None),
)

FACETS_BY_NAME = {f.name: f for f in FACETS}

# Ordre d'affichage des filtres par type d'objet — le plus discriminant d'abord.
FACET_PRIORITY = {
    "dashboard": ("usage", "territoire", "feature", "audience", "theme", "mesure", "source"),
    "conversation": ("feature", "audience", "usage", "theme", "mesure", "source", "territoire"),
    "report": ("feature", "audience", "usage", "theme", "mesure", "source", "territoire"),
}


def normalize_tag_name(raw: str) -> str | None:
    """Minuscules, sans accents, kebab-case. None si vide."""
    stripped = unicodedata.normalize("NFD", raw.strip().lower())
    stripped = "".join(c for c in stripped if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", stripped).strip("-") or None


def normalize_tags(raw_tags: list[str]) -> list[str]:
    return list(dict.fromkeys(t for t in (normalize_tag_name(r) for r in raw_tags) if t is not None))


def ordered_facets(object_type: str) -> tuple[Facet, ...]:
    priority = FACET_PRIORITY.get(object_type, tuple(f.name for f in FACETS))
    return tuple(FACETS_BY_NAME[name] for name in priority if name in FACETS_BY_NAME)


def apply_toggle(current: list[str], name: str, facet_of: dict[str, str]) -> list[str]:
    """Coche/décoche un terme ; une facette à cardinalité 1 se comporte comme un radio."""
    if name in current:
        return [t for t in current if t != name]

    # Why: le plafond des facettes multivaluées guide le tagueur automatique, il ne bride pas l'édition manuelle.
    facet = facet_of.get(name)
    if facet in FACETS_BY_NAME and FACETS_BY_NAME[facet].max_terms == 1:
        current = [t for t in current if facet_of.get(t) != facet]
    return [*current, name]


def load_vocabulary(
    session: Session, *, active_only: bool = True, include_pending: bool = True
) -> dict[str, list[Term]]:
    """Vocabulaire courant groupé par facette, ordonné par libellé."""
    stmt = select(Tag)
    if active_only:
        stmt = stmt.where(Tag.active)
    if not include_pending:
        stmt = stmt.where(~Tag.pending)
    vocab: dict[str, list[Term]] = {}
    for tag in session.scalars(stmt.order_by(Tag.type, Tag.label)):
        vocab.setdefault(tag.type, []).append(
            Term(name=tag.name, label=tag.label, facet=tag.type, description=tag.description, pending=tag.pending)
        )
    return vocab


def load_implications(session: Session) -> dict[str, set[str]]:
    """Nom de tag → noms impliqués (feature → theme, terme précis → terme générique)."""
    implied = aliased(Tag)
    rows = session.execute(
        select(Tag.name, implied.name)
        .join(TagImplication, TagImplication.tag_id == Tag.id)
        .join(implied, implied.id == TagImplication.implies_tag_id)
    ).all()
    result: dict[str, set[str]] = {}
    for name, implied_name in rows:
        result.setdefault(name, set()).add(implied_name)
    return result


def invert_implications(implications: dict[str, set[str]]) -> dict[str, set[str]]:
    """Renverse le graphe : terme générique → termes précis qui l'impliquent."""
    reverse: dict[str, set[str]] = {}
    for source, targets in implications.items():
        for target in targets:
            reverse.setdefault(target, set()).add(source)
    return reverse


def expand_implications(names: list[str], implications: dict[str, set[str]]) -> set[str]:
    """Ajoute transitivement les tags impliqués par ceux posés."""
    expanded = set(names)
    queue = list(names)
    while queue:
        for implied in implications.get(queue.pop(), ()):
            if implied not in expanded:
                expanded.add(implied)
                queue.append(implied)
    return expanded


def build_prompt_taxonomy(vocabulary: dict[str, list[Term]]) -> str:
    """Bloc de taxonomie injecté dans le prompt du tagueur."""
    blocks = []
    for facet in FACETS:
        terms = vocabulary.get(facet.name)
        if not terms:
            continue
        if facet.max_terms == 1:
            rule = "choisir 1 seul"
        elif facet.max_terms:
            rule = f"0 à {facet.max_terms}"
        else:
            rule = "0 à n"
        lines = [f"## {facet.label} ({rule})"]
        lines += [f"- {t.name}: {t.description or t.label}" for t in terms]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
