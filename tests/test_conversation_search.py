"""Recherche de conversations par le sens (embeddings) avec repli sur les mots exacts."""

import math

import pytest

from web import config
from web.database import store
from web.db import get_db
from web.helpers import utcnow
from web.models import ConversationMessageEmbedding, Tag

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

ALICE = "alice@example.com"
BOB = "bob@example.com"


@pytest.fixture(autouse=True)
def embedding_model_ready(mocker):
    mocker.patch("web.routes.html.is_embedding_model_ready", return_value=True)
    mocker.patch("web.routes.conversations.is_embedding_model_ready", return_value=True)


def headers(email=ALICE):
    return {"X-Forwarded-Email": email}


def make_tag(name, facet, label=None):
    with get_db() as session:
        session.add(Tag(name=name, type=facet, label=label or name, active=True))


def unit_vector(axis):
    values = [0.0] * 256
    values[axis] = 1.0
    return values


def embedded_conversation(content, axis, title=None, user_id=ALICE):
    conv = store.create_conversation(user_id=user_id)
    if title:
        store.update_conversation(conv.id, title=title)
    embed_message(conv, content, unit_vector(axis))
    return conv


def embed_message(conv, content, vector, role="user"):
    message = store.add_message(conv.id, role, content)
    with get_db() as session:
        session.add(
            ConversationMessageEmbedding(
                message_id=message.id,
                conversation_id=conv.id,
                user_id=conv.user_id,
                role=role,
                content_hash=f"hash-{message.id}",
                content_length=len(content),
                message_timestamp=utcnow(),
                embedding_model=config.EMBEDDING_MODEL,
                embedding=vector,
            )
        )


def test_similar_groups_by_best_message_and_limits_to_three(client, mocker):
    current = store.create_conversation(user_id=ALICE)
    store.add_message(current.id, "user", "Question actuelle")
    closest = embedded_conversation("Question éloignée", axis=1, title="Fréquentation", user_id=BOB)
    embed_message(closest, "Réponse sur les visites du portail.", unit_vector(0), role="assistant")

    ranked = []
    for cosine in (0.8, 0.6, 0.4):
        conv = store.create_conversation(user_id=BOB)
        vector = [cosine, math.sqrt(1 - cosine**2)] + [0.0] * 254
        embed_message(conv, "Analyse des visites", vector, role="report")
        ranked.append(conv.id)

    embed = mocker.patch("web.routes.conversations.embed_query", return_value=unit_vector(0))
    response = client.get(f"/api/conversations/{current.id}/similar", headers=headers())

    assert response.status_code == 200
    results = response.json()["conversations"]
    assert [conv["id"] for conv in results] == [closest.id, *ranked[:2]]
    assert results[0] == {"id": closest.id, "title": "Fréquentation"}
    embed.assert_called_once_with("Question actuelle")


def test_search_keeps_keywords_while_model_loads_and_adds_semantic_results_when_ready(client, mocker):
    keyword = embedded_conversation("Les candidatures", axis=1, title="Tableau emploi")
    semantic = embedded_conversation("Les visites du portail", axis=0, title="Fréquentation")
    mocker.patch("web.routes.html.is_embedding_model_ready", side_effect=[False, True])
    embed = mocker.patch("web.routes.html.embed_query", return_value=unit_vector(0))

    pending = client.get("/conversations?q=emploi", headers=headers()).text

    assert f"conv-{keyword.id}" in pending
    assert f"conv-{semantic.id}" not in pending
    embed.assert_not_called()

    ready = client.get("/conversations?q=emploi", headers=headers()).text

    assert f"conv-{keyword.id}" in ready
    assert f"conv-{semantic.id}" in ready
    embed.assert_called_once_with("emploi")


def test_dod_9_la_recherche_retrouve_par_le_sens(client, mocker):
    proche = embedded_conversation("les pass IAE des candidats", axis=0, title="Sujet pass")
    loin = embedded_conversation("le conventionnement des employeurs", axis=1, title="Sujet convention")
    mocker.patch("web.routes.html.embed_query", return_value=unit_vector(0))

    html = client.get("/conversations?q=titres+de+sejour", headers=headers()).text

    assert f"conv-{proche.id}" in html
    assert f"conv-{loin.id}" not in html


def test_dod_10_les_mots_exacts_remontent_toujours_meme_avec_des_resultats_par_le_sens(client, mocker):
    titre = embedded_conversation("des structures et du conventionnement", axis=1, title="Tableau de bord emploi")
    sens = embedded_conversation("les visites du portail", axis=0, title="Autre sujet")
    mocker.patch("web.routes.html.embed_query", return_value=unit_vector(0))

    html = client.get("/conversations?q=emploi", headers=headers()).text

    assert f"conv-{titre.id}" in html
    assert f"conv-{sens.id}" in html


def test_dod_11_la_recherche_et_les_filtres_se_combinent(client, mocker):
    make_tag("appli", "feature", "Application")
    avec_tag = embedded_conversation("les pass IAE", axis=0, title="Avec tag")
    store.set_conversation_tags(avec_tag.id, ["appli"])
    sans_tag = embedded_conversation("les pass IAE aussi", axis=0, title="Sans tag")
    mocker.patch("web.routes.html.embed_query", return_value=unit_vector(0))

    html = client.get("/conversations?q=pass&tag=appli", headers=headers()).text

    assert f"conv-{avec_tag.id}" in html
    assert f"conv-{sans_tag.id}" not in html


def test_dod_12_recherche_vide_liste_complete_sans_classement(client, mocker):
    spy = mocker.patch("web.routes.html.embed_query")
    conv = embedded_conversation("peu importe", axis=0, title="Conv sans recherche")

    html = client.get("/conversations", headers=headers()).text

    assert f"conv-{conv.id}" in html
    spy.assert_not_called()


@pytest.mark.parametrize(
    ("params", "visible", "cachee"),
    [
        ("show=mine", ALICE, BOB),
        (f"author={BOB}", BOB, ALICE),
    ],
)
def test_la_recherche_respecte_mes_conversations_et_le_filtre_createur(client, mocker, params, visible, cachee):
    convs = {user: embedded_conversation("les pass IAE", axis=0, title="Pass", user_id=user) for user in (ALICE, BOB)}
    mocker.patch("web.routes.html.embed_query", return_value=unit_vector(0))

    html = client.get(f"/conversations?q=pass&{params}", headers=headers()).text

    assert f"conv-{convs[visible].id}" in html
    assert f"conv-{convs[cachee].id}" not in html


def test_recherche_sans_aucun_resultat(client, mocker):
    conv = embedded_conversation("le conventionnement", axis=1, title="Convention")
    mocker.patch("web.routes.html.embed_query", return_value=unit_vector(0))

    html = client.get("/conversations?q=introuvable", headers=headers()).text

    assert f"conv-{conv.id}" not in html


def test_la_recherche_filtre_aussi_les_rapports_par_titre(client, mocker):
    make_tag("dora", "product", "Dora")
    trouve = store.create_report(title="Rapport pass IAE", content="# Pass", user_id=ALICE)
    ecarte = store.create_report(title="Rapport convention", content="# Convention", user_id=ALICE)
    store.set_report_tags(ecarte.id, ["dora"])
    mocker.patch("web.routes.html.embed_query", return_value=unit_vector(0))

    html = client.get("/conversations?q=pass", headers=headers()).text

    assert trouve.title in html
    assert ecarte.title not in html
