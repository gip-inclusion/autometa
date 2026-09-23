"""Facettes de filtres pour la recherche de conversations — ordre, libellés clairs, épuration."""

from lib.taxonomy import ordered_facets
from web.stores.records import Tag

# Libellés propres à la recherche de conversations, plus parlants que ceux de la taxonomie.
SEARCH_FACET_LABELS = {"audience": "Réseau", "feature": "Bloc fonctionnel"}


def build_search_facets(all_tags: dict[str, list[Tag]]) -> list[dict]:
    """Facettes non vides, dans l'ordre d'affichage des conversations, avec leurs libellés."""
    facets = []
    for facet in ordered_facets("conversation"):
        tags = all_tags.get(facet.name)
        if not tags:
            continue
        facets.append({
            "name": facet.name,
            "label": SEARCH_FACET_LABELS.get(facet.name, facet.label),
            "tags": tags,
        })
    return facets
