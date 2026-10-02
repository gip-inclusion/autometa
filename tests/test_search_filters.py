from web.search_filters import build_search_facets
from web.stores.records import Tag


def _tag(name, facet, label):
    return Tag(name=name, type=facet, label=label)


def test_dod_1_affiche_les_facettes_reelles_dans_l_ordre_conversation():
    all_tags = {
        "product": [_tag("les-emplois", "product", "Les Emplois")],
        "type_demande": [_tag("bug", "type_demande", "Bug")],
        "source": [_tag("matomo", "source", "Matomo")],
        "feature": [_tag("appli", "feature", "Application")],
        "audience": [_tag("siae", "audience", "SIAE")],
    }

    names = [facet["name"] for facet in build_search_facets(all_tags)]

    assert names == ["feature", "audience", "source"]
    assert "product" not in names
    assert "type_demande" not in names


def test_dod_2_renomme_audience_en_reseau_et_feature_en_bloc_fonctionnel():
    all_tags = {
        "audience": [_tag("siae", "audience", "SIAE")],
        "feature": [_tag("appli", "feature", "Application")],
        "usage": [_tag("analyse", "usage", "Analyse")],
        "source": [_tag("matomo", "source", "Matomo")],
    }

    labels = {facet["name"]: facet["label"] for facet in build_search_facets(all_tags)}

    assert labels["audience"] == "Réseau"
    assert labels["feature"] == "Bloc fonctionnel"
    assert labels["usage"] == "Usage"
    assert labels["source"] == "Source"


def test_dod_3_masque_les_categories_sans_tag():
    all_tags = {
        "feature": [_tag("appli", "feature", "Application")],
        "audience": [],
    }

    names = [facet["name"] for facet in build_search_facets(all_tags)]

    assert names == ["feature"]
