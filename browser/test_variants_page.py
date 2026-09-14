"""La page du gabarit multi-sources, assemblée et servie seule : un lien par déclinaison, jamais de liste."""

import http.server
import json
import shutil
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser

TEMPLATES = Path(__file__).parent.parent / "docs"
TOKEN = "00000000-0000-4000-8000-000000000067"
ORPHAN_TOKEN = "00000000-0000-4000-8000-000000000211"


@pytest.fixture(scope="module")
def served(tmp_path_factory):
    root = tmp_path_factory.mktemp("multi")
    for template in ("dashboard-template", "dashboard-template-multi"):
        for src in (TEMPLATES / template).iterdir():
            if src.is_file():
                shutil.copy(src, root / src.name)
    (root / "data").mkdir()
    (root / "data" / f"{TOKEN}.json").write_text(
        json.dumps({
            "metadata": {"generated_at": "2026-09-14", "key": "117", "label": "Emplois"},
            "visites": {"nb_visits": 10},
        })
    )
    handler = type("Quiet", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a: handler(*a, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture
def tracked(page: Page):
    """Le conteneur Matomo ne se charge pas ; on regarde ce que la page lui aurait dit."""
    page.route("**/container_*.js", lambda route: route.fulfill(body="", content_type="application/javascript"))
    return page


def test_dod_1_a_declared_token_shows_that_variant_alone(served, tracked: Page):
    tracked.goto(f"{served}/index.html?q={TOKEN}")

    expect(tracked.locator("#variant-label")).to_have_text("Emplois")
    expect(tracked.locator("#content")).to_be_visible()
    expect(tracked.locator("#generated-at")).to_have_text("2026-09-14")
    expect(tracked.locator("#invalid-link")).to_be_hidden()


@pytest.mark.parametrize(
    "query",
    ["", "?q=", f"?q={ORPHAN_TOKEN.replace('a', 'z')}", f"?q={ORPHAN_TOKEN}"],
    ids=["no-q", "empty-q", "not-a-uuid", "unknown-token"],
)
def test_dod_2_without_a_valid_token_the_page_is_a_dead_end(served, tracked: Page, query):
    tracked.goto(f"{served}/index.html{query}")

    # Why: la page publiée n'a pas la liste des jetons — un jeton bien formé mais inconnu est
    # indiscernable d'une déclinaison sans données ; le message couvre les deux lectures.
    expect(tracked.locator(".error:visible")).to_have_count(1)
    expect(tracked.locator(".error:visible")).to_contain_text("Ce lien n'est pas valide")
    expect(tracked.locator("#content")).to_be_hidden()
    assert tracked.locator("select").count() == 0
    assert tracked.locator("a[href*='?q=']").count() == 0


@pytest.mark.parametrize("query", ["?q=../index.html", "?q=abc", "?q=data/x"], ids=["traversal", "short", "path"])
def test_dod_13_a_malformed_token_triggers_no_request(served, tracked: Page, query):
    data_requests = []
    tracked.on("request", lambda request: data_requests.append(request.url) if "/data/" in request.url else None)

    tracked.goto(f"{served}/index.html{query}")

    expect(tracked.locator("#invalid-link")).to_be_visible()
    assert data_requests == []


def test_dod_14_a_valid_token_without_data_file_says_so(served, tracked: Page):
    tracked.goto(f"{served}/index.html?q={ORPHAN_TOKEN}")

    expect(tracked.locator("#no-data")).to_be_visible()
    expect(tracked.locator("#no-data")).to_contain_text("pas encore disponibles")
    expect(tracked.locator("#invalid-link")).to_be_hidden()


def test_dod_19_matomo_sees_the_key_never_the_token(served, tracked: Page):
    tracked.goto(f"{served}/index.html?q={TOKEN}")
    expect(tracked.locator("#variant-label")).to_have_text("Emplois")

    paq = tracked.evaluate("window._paq")
    assert ["setCustomUrl", f"{served}/117/"] in paq
    assert ["setDocumentTitle", "Emplois"] in paq
    assert ["HeatmapSessionRecording::disable"] in paq
    assert TOKEN not in json.dumps(paq)
    assert tracked.title() == "Emplois"
    assert tracked.locator("script[src*='container_']").count() == 1
