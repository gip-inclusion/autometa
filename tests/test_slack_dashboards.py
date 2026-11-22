"""Un tableau de bord en Work Object de Slack : quelles adresses, ce que l'objet dit selon le site, son volet."""

from datetime import datetime, timezone

import pytest

from lib.taxonomy import Term
from web import config, slack_dashboards
from web.environment import Environment
from web.stores.records import Conversation

BASE = "https://autometa.example"
PUBLIC = "https://statistiques.example"
INTERNAL = f"{BASE}/interactive/suivi-iae/"
CREATED = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)
UPDATED = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)
PUBLISHED = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
RUN = datetime(2026, 11, 21, 6, 0, tzinfo=timezone.utc)
PUBLICATION = {"environment": "production", "published_at": PUBLISHED, "url": f"{PUBLIC}/dashboards/suivi-iae"}


def dashboard(**fields):
    defaults = {
        "slug": "suivi-iae",
        "title": "Suivi de l'IAE",
        "description": "Les candidatures\npar département.",
        "website": "emplois",
        "tags": ["siae", "suivi"],
        "first_author_email": "camille.martin@example.org",
        "conversation_id": "0a1b2c3d",
        "created_at": CREATED,
        "updated": UPDATED,
        "is_archived": False,
        "has_cron": True,
        "cron_enabled": True,
        "cron_schedule": "weekly",
    }
    return defaults | fields


@pytest.fixture(autouse=True)
def instance(monkeypatch):
    monkeypatch.setattr(config, "BASE_URL", BASE)
    monkeypatch.setattr(config, "PUBLIC_DASHBOARDS_PROD_URL", PUBLIC)
    monkeypatch.setattr(config, "ENV", Environment.PROD)


def known(mocker, found=None, published=(PUBLICATION,), variants=0, run=RUN, origin="Une conversation"):
    """Un tableau de bord connu de l'instance, ses publications actives, ses déclinaisons, son dernier calcul."""
    found = found or dashboard()
    mocker.patch.object(slack_dashboards.store, "get_dashboard", return_value=found)
    mocker.patch.object(slack_dashboards.publications, "list_publications", return_value=list(published))
    listed = [{"key": str(rank), "label": f"Secret {rank}", "token": f"jeton-{rank}"} for rank in range(variants)]
    mocker.patch.object(slack_dashboards.variants, "list_variants", return_value=listed)
    runs = {found["slug"]: {"started_at": run, "status": "success"}} if run else {}
    mocker.patch.object(slack_dashboards.cron, "get_last_runs", return_value=runs)
    conv = Conversation(id="0a1b2c3d", title=origin) if origin is not None else None
    mocker.patch.object(slack_dashboards.store, "get_conversation", return_value=conv)
    mocker.patch.object(slack_dashboards, "get_db")
    vocabulary = {
        "audience": [Term("siae", "SIAE", "audience"), Term("autre", "Autre", "audience")],
        "usage": [Term("suivi", "Suivi", "usage")],
    }
    mocker.patch.object(slack_dashboards, "load_vocabulary", return_value=vocabulary)


@pytest.mark.parametrize(
    "url,expected",
    [
        (f"{BASE}/interactive/suivi-iae", ("suivi-iae", False)),
        (f"{BASE}/interactive/suivi-iae/?q=jeton#haut", ("suivi-iae", False)),
        (f"{BASE}/interactive/suivi-iae/data/x.json", ("suivi-iae", False)),
        (f"{BASE}/dashboards/suivi_iae-2", ("suivi_iae-2", False)),
        (f"{BASE}/dashboards/suivi-iae/edit", ("suivi-iae", False)),
        ("https://AUTOMETA.example/interactive/suivi-iae/", ("suivi-iae", False)),
        (f"{PUBLIC}/dashboards/suivi-iae", ("suivi-iae", True)),
        (f"{PUBLIC}/dashboards/suivi-iae/index.html?q=78", ("suivi-iae", True)),
        (f"{PUBLIC}/interactive/suivi-iae/", None),
        (f"{PUBLIC}/", None),
        (f"{BASE}/interactive/export.csv", None),
        (f"{BASE}/interactive/", None),
        (f"{BASE}/dashboards", None),
        (f"{BASE}/c/0a1b2c3d", None),
        ("https://staging.statistiques.example/dashboards/suivi-iae-ab12cd", None),
        (f"https://evil.test/{PUBLIC}/dashboards/suivi-iae", None),
        ("https://[bad/dashboards/suivi-iae", None),
    ],
)
def test_only_a_dashboard_address_of_this_instance_or_the_public_site_names_a_dashboard(url, expected):
    assert slack_dashboards.located(url) == expected


@pytest.mark.parametrize("env", [Environment.DEV, Environment.REVIEW, Environment.STAGING])
def test_only_production_answers_for_the_public_site(monkeypatch, env):
    monkeypatch.setattr(config, "ENV", env)

    assert slack_dashboards.located(f"{PUBLIC}/dashboards/suivi-iae") is None
    assert slack_dashboards.located(INTERNAL) == ("suivi-iae", False)


def test_an_internal_link_is_an_object_with_title_description_author_dates_and_state(mocker):
    known(mocker, variants=12)

    assert slack_dashboards.entity(INTERNAL) == {
        "url": INTERNAL,
        "external_ref": {"id": "suivi-iae"},
        "entity_type": "slack#/entities/content_item",
        "entity_payload": {
            "attributes": {
                "title": {"text": "Suivi de l'IAE"},
                "display_type": "Tableau de bord",
                "product_name": "Autometa",
                "metadata_last_modified": int(PUBLISHED.timestamp()),
            },
            "fields": {
                "description": {"value": "Les candidatures par département."},
                "created_by": {
                    "type": "slack#/types/user",
                    "user": {"text": "camille.martin", "email": "camille.martin@example.org"},
                },
                "date_created": {"value": int(CREATED.timestamp())},
                "date_updated": {"value": int(UPDATED.timestamp())},
            },
            "custom_fields": [
                {"key": "state", "label": "État", "value": "Publié", "type": "string", "tag_color": "green"},
                {"key": "variants", "label": "Déclinaisons", "value": 12, "type": "integer"},
            ],
        },
    }


def custom(url=INTERNAL, detailed=False):
    return {shown["key"]: shown for shown in slack_dashboards.entity(url, detailed)["entity_payload"]["custom_fields"]}


@pytest.mark.parametrize(
    "fields,published,state",
    [
        ({}, [], None),
        ({}, [PUBLICATION | {"environment": "staging"}], None),
        ({"is_archived": True}, [], "Archivé"),
        ({"is_archived": True}, [PUBLICATION], "Archivé"),
    ],
    ids=["private", "published to staging only", "archived", "archived and published"],
)
def test_the_state_tells_archived_before_published_and_nothing_for_a_private_dashboard(
    mocker, fields, published, state
):
    known(mocker, dashboard(**fields), published)

    assert custom().get("state", {}).get("value") == state


def test_a_public_link_only_tells_title_description_and_publication_date(mocker):
    known(mocker, variants=12)
    url = f"{PUBLIC}/dashboards/suivi-iae"

    shown = slack_dashboards.entity(url, detailed=True)

    assert shown["url"] == url
    assert shown["external_ref"] == slack_dashboards.entity(INTERNAL)["external_ref"]
    assert shown["entity_payload"]["attributes"]["title"] == {"text": "Suivi de l'IAE"}
    assert shown["entity_payload"]["fields"] == {"description": {"value": "Les candidatures par département."}}
    assert shown["entity_payload"]["custom_fields"] == [
        {
            "key": "published",
            "label": "Publication",
            "value": int(PUBLISHED.timestamp()),
            "type": "slack#/types/timestamp",
        }
    ]


@pytest.mark.parametrize(
    "url,found,published",
    [
        (INTERNAL, None, [PUBLICATION]),
        (f"{PUBLIC}/dashboards/suivi-iae", None, [PUBLICATION]),
        (f"{PUBLIC}/dashboards/suivi-iae", dashboard(), []),
        (f"{PUBLIC}/dashboards/suivi-iae", dashboard(), [PUBLICATION | {"environment": "staging"}]),
        (f"{BASE}/c/0a1b2c3d", dashboard(), [PUBLICATION]),
    ],
    ids=["unknown slug", "unknown public slug", "unpublished", "published to staging only", "not a dashboard"],
)
def test_an_unknown_dashboard_or_an_unpublished_public_link_makes_no_object(mocker, url, found, published):
    known(mocker, published=published)
    slack_dashboards.store.get_dashboard.return_value = found

    assert slack_dashboards.entity(url) is None


def test_the_pane_adds_product_refresh_links_and_tags_by_facet(mocker):
    known(mocker, variants=3)

    assert list(custom(detailed=True).values()) == [
        {"key": "state", "label": "État", "value": "Publié", "type": "string", "tag_color": "green"},
        {"key": "variants", "label": "Déclinaisons", "value": 3, "type": "integer"},
        {"key": "product", "label": "Produit", "value": "emplois", "type": "string"},
        {"key": "cadence", "label": "Actualisation", "value": "Chaque semaine", "type": "string"},
        {
            "key": "last_run",
            "label": "Dernière actualisation",
            "value": int(RUN.timestamp()),
            "type": "slack#/types/timestamp",
        },
        {
            "key": "public",
            "label": "Version publique",
            "value": "statistiques.example/dashboards/suivi-iae",
            "type": "string",
            "link": f"{PUBLIC}/dashboards/suivi-iae",
        },
        {
            "key": "origin",
            "label": "Conversation d'origine",
            "value": "Une conversation",
            "type": "string",
            "link": f"{BASE}/c/0a1b2c3d",
        },
        {
            "key": "tags_usage",
            "label": "Usage",
            "type": "array",
            "item_type": "string",
            "value": [{"value": "Suivi"}],
        },
        {
            "key": "tags_audience",
            "label": "Public",
            "type": "array",
            "item_type": "string",
            "value": [{"value": "SIAE"}],
        },
    ]


@pytest.mark.parametrize(
    "fields,more,absent",
    [
        ({"website": None}, {}, "product"),
        ({"has_cron": False}, {}, "cadence"),
        ({"cron_enabled": False}, {}, "cadence"),
        ({"has_cron": False}, {}, "last_run"),
        ({}, {"run": None}, "last_run"),
        ({}, {"published": []}, "public"),
        ({"conversation_id": None}, {}, "origin"),
        ({}, {"origin": None}, "origin"),
        ({"tags": []}, {}, "tags_usage"),
        ({}, {}, "variants"),
    ],
)
def test_the_pane_only_holds_what_the_dashboard_has(mocker, fields, more, absent):
    known(mocker, dashboard(**fields), **more)

    assert absent not in custom(detailed=True)


def test_neither_labels_nor_tokens_of_variants_ever_show(mocker):
    known(mocker, variants=2)

    for url in (f"{INTERNAL}?q=jeton-1", f"{PUBLIC}/dashboards/suivi-iae?q=jeton-1"):
        shown = str(slack_dashboards.entity(url, detailed=True) | {"url": ""})
        assert "Secret" not in shown
        assert "jeton" not in shown


def test_nothing_a_dashboard_says_can_mention_or_link(mocker):
    hostile = "<!channel> @here http://evil.example \u202egauche"
    known(mocker, dashboard(title=hostile, description=hostile, website=hostile), origin=hostile)

    shown = slack_dashboards.entity(INTERNAL, detailed=True)["entity_payload"]
    safe = "<\u200b!channel> @\u200bhere http:\u200b//evil.example gauche"

    assert shown["attributes"]["title"]["text"] == safe
    assert shown["fields"]["description"]["value"] == safe
    values = {field["key"]: field["value"] for field in shown["custom_fields"]}
    assert (values["product"], values["origin"]) == (safe, safe)


@pytest.mark.parametrize(
    "published,moment",
    [([], UPDATED), ([PUBLICATION], PUBLISHED), ([PUBLICATION | {"published_at": CREATED}], UPDATED)],
    ids=["private", "published since its last change", "changed since its publication"],
)
def test_the_object_is_dated_by_its_last_change_or_publication_so_an_unchanged_one_refreshes_nothing(
    mocker, published, moment
):
    known(mocker, published=published)

    shown = slack_dashboards.entity(INTERNAL, detailed=True)["entity_payload"]["attributes"]

    assert shown["metadata_last_modified"] == int(moment.timestamp())
