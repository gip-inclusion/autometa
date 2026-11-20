"""Facettes de filtres pour la recherche de conversations — ordre, libellés clairs, épuration."""

from lib.taxonomy import FACETS_BY_NAME, ordered_facets
from web.stores.records import Tag

# Libellés propres à la recherche de conversations, plus parlants que ceux de la taxonomie.
SEARCH_FACET_LABELS = {"audience": "Réseau", "feature": "Bloc fonctionnel"}

# Facettes dépliées d'emblée, dans cet ordre ; les autres suivent, repliées.
SEARCH_OPEN_FACETS = ("theme", "audience", "feature")


def build_search_facets(all_tags: dict[str, list[Tag]]) -> list[dict]:
    """Facettes non vides, celles dépliées d'emblée en tête, avec leurs libellés."""
    others = [f.name for f in ordered_facets("conversation") if f.name not in SEARCH_OPEN_FACETS]
    return [
        {
            "name": name,
            "label": SEARCH_FACET_LABELS.get(name, FACETS_BY_NAME[name].label),
            "tags": all_tags[name],
            "folded": name not in SEARCH_OPEN_FACETS,
        }
        for name in (*SEARCH_OPEN_FACETS, *others)
        if all_tags.get(name)
    ]
