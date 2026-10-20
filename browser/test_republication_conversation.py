"""L'alerte « republier » dans la conversation : affichée si un tableau publié a dérivé, sinon absente."""

import http.server
import json
import shutil
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser

STREAM_JS = Path(__file__).parent.parent / "web" / "static" / "js" / "stream.js"
CONV_ID = "00000000-0000-4000-8000-000000000217"

PAGE = (
    '<!doctype html><html><head><meta charset="utf-8"></head>'
    '<body><div id="chatOutput"></div><script src="stream.js"></script></body></html>'
)


@pytest.fixture
def served(tmp_path_factory):
    root = tmp_path_factory.mktemp("conv")
    shutil.copy(STREAM_JS, root / "stream.js")
    (root / "index.html").write_text(PAGE)
    handler = type("Quiet", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a: handler(*a, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def _stub_dashboards(page: Page, drifted):
    page.route(
        "**/api/conversations/**/dashboards",
        lambda route: route.fulfill(body=json.dumps({"drifted": drifted}), content_type="application/json"),
    )


def test_dod_10_the_conversation_alerts_that_a_published_dashboard_needs_republishing(served, page: Page):
    _stub_dashboards(page, [{"slug": "mon-tdb", "title": "Mon TDB"}])
    page.goto(f"{served}/index.html")
    page.evaluate(f"showRepublishAlert('{CONV_ID}')")

    alert = page.locator("#republish-alert")
    expect(alert).to_be_visible()
    expect(alert).to_contain_text("republiez")
    link = alert.locator("a")
    expect(link).to_have_attribute("href", "/dashboards/mon-tdb/edit")
    expect(link).to_contain_text("Mon TDB")


def test_dod_11_no_alert_when_no_published_dashboard_has_drifted(served, page: Page):
    _stub_dashboards(page, [])
    page.goto(f"{served}/index.html")
    page.evaluate(f"showRepublishAlert('{CONV_ID}')")

    expect(page.locator("#republish-alert")).to_have_count(0)
