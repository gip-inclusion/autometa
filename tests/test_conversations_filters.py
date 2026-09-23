"""Menu de filtres de la recherche de conversations — épuration, état vide, filtre fantôme."""

import pytest

from web.database import store
from web.db import get_db
from web.models import Tag

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

ALICE = "alice@example.com"


def headers(email=ALICE):
    return {"X-Forwarded-Email": email}


def make_tag(name, facet, label=None):
    with get_db() as session:
        session.add(Tag(name=name, type=facet, label=label or name, active=True))


def tagged_conversation(tag_names, user_id=ALICE, title=None):
    conv = store.create_conversation(user_id=user_id)
    if title:
        store.update_conversation(conv.id, title=title)
    store.set_conversation_tags(conv.id, tag_names)
    return conv


def test_dod_5_un_filtre_restreint_plusieurs_se_combinent_et_s_effacent(client):
    make_tag("appli", "feature", "Application")
    make_tag("siae", "audience", "SIAE")
    c_appli = tagged_conversation(["appli"], title="Conv appli")
    c_both = tagged_conversation(["appli", "siae"], title="Conv both")
    c_other = tagged_conversation(["siae"], title="Conv siae")

    narrowed = client.get("/conversations?tag=appli", headers=headers()).text
    assert f"conv-{c_appli.id}" in narrowed
    assert f"conv-{c_both.id}" in narrowed
    assert f"conv-{c_other.id}" not in narrowed
    assert 'class="filter-dropdown-btn active"' in narrowed

    combined = client.get("/conversations?tag=appli&tag=siae", headers=headers()).text
    assert f"conv-{c_both.id}" in combined
    assert f"conv-{c_appli.id}" not in combined

    full = client.get("/conversations", headers=headers()).text
    assert f"conv-{c_appli.id}" in full
    assert f"conv-{c_other.id}" in full


def test_dod_6_filtre_actif_visible_coche_et_conserve_au_rechargement(client):
    make_tag("appli", "feature", "Application")
    tagged_conversation(["appli"], title="Conv appli")

    html = client.get("/conversations?tag=appli", headers=headers()).text

    assert 'data-tag="appli"' in html
    assert "checked" in html
    assert 'class="filter-count"' in html


def test_dod_7_message_et_effacement_quand_les_filtres_ne_donnent_rien(client):
    make_tag("appli", "feature", "Application")
    make_tag("siae", "audience", "SIAE")
    tagged_conversation(["appli"])
    tagged_conversation(["siae"])

    r = client.get("/conversations?tag=appli&tag=siae", headers=headers())

    assert r.status_code == 200
    assert "Aucun résultat" in r.text
    assert "Effacer les filtres" in r.text


def test_dod_8_filtre_fantome_ignore_et_liste_non_videe(client):
    make_tag("appli", "feature", "Application")
    conv = tagged_conversation(["appli"], title="Ma conversation")

    r = client.get("/conversations?tag=fantome-inexistant", headers=headers())

    assert r.status_code == 200
    assert f"conv-{conv.id}" in r.text
    assert "Aucun résultat" not in r.text
