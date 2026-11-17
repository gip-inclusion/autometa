"""Recherche de conversations et de rapports par mots."""

import pytest

from web.database import store
from web.db import get_db
from web.models import Tag

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

ALICE = "alice@example.com"
BOB = "bob@example.com"


def headers(email=ALICE):
    return {"X-Forwarded-Email": email}


def make_tag(name, facet, label=None):
    with get_db() as session:
        session.add(Tag(name=name, type=facet, label=label or name, active=True))


def conversation(content, title="Sujet", user_id=ALICE):
    conv = store.create_conversation(user_id=user_id)
    store.update_conversation(conv.id, title=title)
    store.add_message(conv.id, "user", content)
    return conv


def search(client, q, extra=None):
    return client.get("/conversations", params={"q": q, **(extra or {})}, headers=headers()).text


@pytest.mark.parametrize(
    ("q", "trouvee"),
    [
        ("pass", True),
        ("pass candidats", True),
        ("candidats pass", True),
        ("pass employeurs", False),
        ("50%", False),
        ("IAE_des", False),
        ("introuvable", False),
    ],
)
def test_la_recherche_par_mots(client, q, trouvee):
    conv = conversation("les pass IAE des candidats, 50 points")

    assert (f"conv-{conv.id}" in search(client, q)) is trouvee


def test_les_mots_peuvent_venir_du_titre_et_des_messages(client):
    conv = conversation("les candidats", title="Pass IAE")

    assert f"conv-{conv.id}" in search(client, "pass candidats")


def test_une_conversation_aux_nombreux_messages_ne_masque_pas_les_autres(client):
    ancienne = conversation("parlons du pass IAE")
    bavarde = conversation("le pass")
    for _ in range(120):
        store.add_message(bavarde.id, "assistant", "encore le pass")

    html = search(client, "pass")

    assert f"conv-{bavarde.id}" in html
    assert f"conv-{ancienne.id}" in html


def test_la_recherche_et_les_filtres_se_combinent(client):
    make_tag("appli", "feature", "Application")
    avec_tag = conversation("les pass IAE")
    store.set_conversation_tags(avec_tag.id, ["appli"])
    sans_tag = conversation("les pass IAE aussi")

    html = search(client, "pass", {"tag": "appli"})

    assert f"conv-{avec_tag.id}" in html
    assert f"conv-{sans_tag.id}" not in html


@pytest.mark.parametrize(
    ("params", "visible", "cachee"), [({"show": "mine"}, ALICE, BOB), ({"author": BOB}, BOB, ALICE)]
)
def test_la_recherche_respecte_mes_conversations_et_le_filtre_createur(client, params, visible, cachee):
    convs = {user: conversation("les pass IAE", user_id=user) for user in (ALICE, BOB)}

    html = search(client, "pass", params)

    assert f"conv-{convs[visible].id}" in html
    assert f"conv-{convs[cachee].id}" not in html


def test_recherche_vide_liste_complete(client):
    conv = conversation("peu importe")

    assert f"conv-{conv.id}" in client.get("/conversations", headers=headers()).text


@pytest.mark.parametrize(
    ("q", "trouve"), [("pass", True), ("pass rapport", True), ("pass convention", False), ("100%", False)]
)
def test_la_recherche_de_rapports_par_mots(client, q, trouve):
    rapport = store.create_report(title="Rapport pass IAE 100 jours", content="x", user_id=ALICE)

    assert (rapport.title in search(client, q)) is trouve


def test_un_rapport_hors_des_cent_plus_recents_reste_trouvable(client):
    ancien = store.create_report(title="Rapport zorglub", content="x", user_id=ALICE)
    for i in range(101):
        store.create_report(title=f"Autre {i}", content="x", user_id=ALICE)

    assert ancien.title in search(client, "zorglub")
