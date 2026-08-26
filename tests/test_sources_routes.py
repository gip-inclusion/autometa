"""Pages /sources et /sources/<slug>."""

import fakeredis.aioredis
import pytest

from web.routes import sources as sources_routes

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]


@pytest.fixture(autouse=True)
def isolated_probe_cache(mocker):
    """Un Redis neuf par test : le cache de sondes ne doit pas fuir d'un test à l'autre."""
    mocker.patch("web.routes.sources.get_redis", return_value=fakeredis.aioredis.FakeRedis(decode_responses=True))


def test_page_is_reachable_and_linked_from_the_menu(client):
    response = client.get("/sources")
    assert response.status_code == 200
    assert 'href="/sources"' in response.text
    assert 'href="/knowledge"' in response.text


@pytest.mark.parametrize("path", ["/sources", "/sources/matomo", "/sources/matomo/access"])
def test_pages_are_open_to_non_admins(client, path):
    """DOD-1 : la page s'adresse à tout le monde, c'est une partie de son intérêt."""
    from web.config import ADMIN_USERS

    visitor = "visiteuse@inclusion.gouv.fr"
    assert visitor not in ADMIN_USERS

    assert client.get(path, headers={"X-Forwarded-Email": visitor}).status_code == 200


@pytest.mark.parametrize(
    "old,new",
    [
        ("/connaissances", "/knowledge"),
        ("/connaissances/sites/emplois.md", "/knowledge/sites/emplois.md"),
        # Fiche disparue : on retombe sur l'index plutôt que sur une page d'erreur.
        ("/connaissances/sources/disparue.md", "/knowledge"),
        ("/connaissances?section=sites", "/knowledge?section=sites"),
        # Ancien motif ?file= : la validation empêche une redirection ouverte.
        ("/connaissances?file=sites/emplois.md", "/knowledge?file=sites/emplois.md"),
    ],
)
def test_french_knowledge_urls_still_redirect(client, old, new):
    """Des liens vers l'ancienne URL vivent dans les messages déjà enregistrés."""
    response = client.get(old, follow_redirects=False)
    assert response.status_code == 301
    assert response.headers["location"] == new


HOSTILE_PATHS = [
    "https://evil.test/phish",
    "../../../etc/passwd",
    "..%2f..%2fevil",
    "//evil.test/phish",
    "/etc/passwd",
    "sites/../../secret",
]


@pytest.mark.parametrize(
    "file,expected",
    [("sites/emplois.md", "/knowledge/sites/emplois.md"), *[(p, "/knowledge") for p in HOSTILE_PATHS]],
)
def test_legacy_file_parameter_cannot_be_steered(client, file, expected):
    """L'ancien motif ?file= mène à une fiche ou à l'index, jamais ailleurs."""
    response = client.get(f"/knowledge?file={file}", follow_redirects=False)

    assert response.status_code == 301
    assert response.headers["location"] == expected


@pytest.mark.parametrize("payload", HOSTILE_PATHS)
def test_legacy_path_redirect_cannot_be_steered(client, payload):
    """L'ancienne URL /connaissances/<chemin> valide son chemin comme le fait ?file=."""
    response = client.get(f"/connaissances/{payload}", follow_redirects=False)

    assert response.status_code in (301, 404)
    if response.status_code == 301:
        location = response.headers["location"]
        assert location == "/knowledge" or location.startswith("/knowledge/")
        assert ".." not in location
        assert "//" not in location.removeprefix("/knowledge")


def test_page_groups_sources_by_role(client):
    body = client.get("/sources").text
    for group in ("Données métier", "Analytiques web", "Connecteurs", "Interne"):
        assert group in body


def test_card_shows_name_blurb_and_skill(client):
    body = client.get("/sources").text
    assert "autometa_tables_db" in body
    assert "Source prioritaire" in body
    assert "metabase_query" in body


def test_initial_render_probes_nothing(client, mocker):
    """DOD-5 : la page part sans sonde ; les accès arrivent ensuite."""
    spy = mocker.spy(sources_routes, "probe")
    body = client.get("/sources").text

    assert spy.call_count == 0
    assert 'hx-get="/sources/matomo/access"' in body


def test_probe_slots_do_not_inherit_the_card_navigation(client):
    """hx-target/hx-select/hx-push-url s'héritent : une sonde ne repeint pas la page et n'entre pas dans l'historique."""
    body = client.get("/sources").text
    slot = body[body.index('hx-get="/sources/') :]
    slot = slot[: slot.index("</span>")]

    assert 'hx-target="this"' in slot
    assert 'hx-push-url="false"' in slot
    assert 'hx-select="unset"' in slot


def test_access_fragment_reports_an_unconfigured_source(client, mocker):
    mocker.patch.object(sources_routes, "probe", return_value={"state": "unconfigured", "detail": "rien"})
    response = client.get("/sources/matomo/access")

    assert response.status_code == 200
    assert "Non configuré ici" in response.text


@pytest.mark.parametrize(
    "state,expected",
    [("ok", "Joignable"), ("ko", "Injoignable")],
)
def test_access_fragment_renders_each_state(client, mocker, state, expected):
    mocker.patch.object(sources_routes, "probe", return_value={"state": state, "detail": "détail"})
    assert expected in client.get("/sources/matomo/access").text


def test_detail_page_renders_the_agent_document(client):
    """DOD-9 : la page affiche le document que lit l'agent, ici un SKILL.md, sans son en-tête YAML."""
    body = client.get("/sources/autometa-tables-db").text

    assert "documentation.doc_autometa_tables" in body
    assert "skills/autometa_tables_db/SKILL.md" in body
    assert "description: Query autometa_tables_db" not in body


def test_detail_page_links_a_knowledge_document(client):
    body = client.get("/sources/matomo").text
    assert 'href="/knowledge/matomo/README.md"' in body


def test_source_without_documentation_says_so(client):
    body = client.get("/sources/s3").text
    assert "pas encore de documentation" in body


def test_unknown_source_is_not_found(client):
    assert client.get("/sources/inexistante").status_code == 404
    assert client.get("/sources/inexistante/access").status_code == 404


@pytest.mark.parametrize("bad_slug", ["UPPER", "with.dot", "with$dollar", "a" * 61])
def test_invalid_slug_rejected(client, bad_slug):
    assert client.get(f"/sources/{bad_slug}").status_code == 422


def catalog_stub(mocker, rows):
    from lib.query import QueryResult
    from web import source_inventories

    return mocker.patch.object(
        source_inventories,
        "execute_autometa_tables_query",
        return_value=QueryResult(success=True, data={"columns": [], "rows": rows, "row_count": len(rows)}),
    )


def test_the_catalog_panel_renders_schemas_tables_and_columns(client, mocker):
    """DOD-7 : le dictionnaire de données devient consultable sans écrire de SQL."""
    catalog_stub(mocker, [["les_emplois", "candidatures", "Les candidatures", "id", "text", "Identifiant"]])

    body = client.get("/sources/autometa-tables-db").text

    assert "les_emplois" in body
    assert "candidatures" in body
    assert "Identifiant" in body


def test_the_catalog_panel_accepts_a_filter(client, mocker):
    catalog_stub(mocker, [["les_emplois", "candidatures", None, "id", "text", None]])

    assert "Aucune table ne correspond" in client.get("/sources/autometa-tables-db?q=introuvable").text


def test_a_source_without_inventory_shows_no_contents_panel(client):
    assert "source-contents" not in client.get("/sources/s3").text


def test_the_connector_panel_lists_what_the_last_sync_stored(client):
    """DOD-5 : les racines Notion collectées sont affichées."""
    from lib.source_inventory import InventoryItem, replace_inventory

    replace_inventory("notion", [InventoryItem(item_type="database", external_id="db-1", label="Suivi bizdev")])

    assert "Suivi bizdev" in client.get("/sources/notion").text
