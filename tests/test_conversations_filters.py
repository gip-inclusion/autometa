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


def test_dod_13_filtre_par_personne(client):
    make_tag("appli", "feature", "Application")
    alice = tagged_conversation(["appli"], user_id="alice@example.com", title="Conv Alice")
    bob = tagged_conversation(["appli"], user_id="bob@example.com", title="Conv Bob")

    filtered = client.get("/conversations?author=alice@example.com", headers=headers()).text
    assert "Créé par" in filtered
    assert f"conv-{alice.id}" in filtered
    assert f"conv-{bob.id}" not in filtered

    combined = client.get("/conversations?author=bob@example.com&tag=appli", headers=headers()).text
    assert f"conv-{bob.id}" in combined
    assert f"conv-{alice.id}" not in combined


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


def test_cocher_un_filtre_ne_deplace_pas_les_autres_termes(client):
    make_tag("frequent", "theme", "Zèbre")
    make_tag("rare", "theme", "Abeille")
    tagged_conversation(["frequent"])
    tagged_conversation(["frequent"])
    tagged_conversation(["rare"])

    for url in ("/conversations", "/conversations?tag=rare"):
        html = client.get(url, headers=headers()).text
        assert html.index('data-tag="frequent"') < html.index('data-tag="rare"')


@pytest.mark.parametrize(("active", "unfolded"), [("t6", True), ("t1", False), (None, False)])
def test_voir_plus_replie_les_termes_apres_le_cinquieme_sauf_si_l_un_est_coche(client, active, unfolded):
    for i in range(1, 7):
        make_tag(f"t{i}", "theme", f"Terme {i}")
        tagged_conversation([f"t{i}"])

    html = client.get("/conversations", params={"tag": active} if active else {}, headers=headers()).text

    theme = html[html.index('<div class="filter-section-title">Thème') :]
    shown, overflow = theme.split("<details", 1)
    assert 'data-tag="t5"' in shown
    assert 'data-tag="t6"' not in shown
    assert 'data-tag="t6"' in overflow
    assert overflow.startswith(' class="filter-overflow filter-overflow-small" open>') is unfolded
