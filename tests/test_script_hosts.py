"""Sites d'où une page de TDB charge un script, aux moments où elle passe : écriture, adoption, audit."""

import pytest
from sqlalchemy import delete

from lib import dashboards, script_hosts
from web import config, cron, csp
from web.db import get_db
from web.helpers import utcnow
from web.models import Dashboard

ALLOWED_PAGE = (
    '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>\n'
    "<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>\n"
    '<script src="app.js"></script><script src="/interactive/tdb/lib.js"></script>\n'
    "<script>window.ok = 1;</script>"
)
OFFENDING_PAGE = '<script src="https://gestaltfabrik.github.io/fluo-proto/static/vendor/jquery/jquery.min.js"></script>'


@pytest.mark.parametrize(
    ("html", "blocked"),
    [
        (ALLOWED_PAGE, []),
        ('<script src="https://d3js.org/d3.v7.min.js" defer></script>', []),
        ("<script src=//unpkg.com/htmx.org@2.0.4></script>", []),
        (OFFENDING_PAGE, ["https://gestaltfabrik.github.io/fluo-proto/static/vendor/jquery/jquery.min.js"]),
        (
            '<script src="https://cdn.jsdelivr.net/gh/user/repo/x.js"></script>',
            ["https://cdn.jsdelivr.net/gh/user/repo/x.js"],
        ),
        (
            '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>',
            ["https://cdn.plot.ly/plotly-2.35.2.min.js"],
        ),
        ('<script src="https://unpkg.com.evil.example/x.js"></script>', ["https://unpkg.com.evil.example/x.js"]),
        ('<script src="http://unpkg.com/x.js"></script>', ["http://unpkg.com/x.js"]),
        ('<SCRIPT type="module" SRC="data:text/javascript,alert(1)"></SCRIPT>', ["data:text/javascript,alert(1)"]),
    ],
)
def test_script_host_violations(html, blocked):
    assert script_hosts.script_host_violations(html) == blocked


def test_the_policy_allows_the_same_sites_the_write_checks_enforce():
    assert all(host in csp.policy() for host in script_hosts.ALLOWED)


@pytest.mark.parametrize("template_dir", ["dashboard-template", "dashboard-template-multi"])
def test_template_loads_scripts_from_allowed_sites_only(template_dir):
    page = config.BASE_DIR / "docs" / template_dir / "index.html"
    assert script_hosts.script_host_violations(page.read_text()) == []


def dashboard_files(mocker, tmp_path, files):
    mocker.patch.object(dashboards.config, "INTERACTIVE_DIR", tmp_path)
    for name, body in files.items():
        (tmp_path / "tdb" / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "tdb" / name).write_text(body)


@pytest.mark.parametrize(
    ("files", "problems"),
    [
        ({"index.html": ALLOWED_PAGE, "app.js": OFFENDING_PAGE}, []),
        (
            {"index.html": ALLOWED_PAGE, "marseille/profil.HTML": OFFENDING_PAGE},
            [
                "marseille/profil.HTML charge https://gestaltfabrik.github.io/fluo-proto/static/vendor/jquery/jquery.min.js"
            ],
        ),
    ],
)
def test_script_host_problems(mocker, tmp_path, files, problems):
    dashboard_files(mocker, tmp_path, files)
    assert dashboards.script_host_problems("tdb") == problems


def test_script_host_problems_refuses_a_slug_that_escapes_the_dashboards_directory():
    with pytest.raises(ValueError, match="[Ss]lug"):
        dashboards.script_host_problems("../../etc")


def test_adopting_a_dashboard_that_loads_a_forbidden_script_is_refused_before_registration(mocker, tmp_path):
    dashboard_files(mocker, tmp_path, {"index.html": OFFENDING_PAGE})
    db = mocker.patch.object(dashboards, "get_db")

    with pytest.raises(ValueError, match="gestaltfabrik"):
        dashboards.adopt_dashboard(
            slug="tdb",
            title="T",
            description=None,
            website=None,
            category=None,
            tags=[],
            first_author_email="a@b.c",
            created_in_conversation_id=None,
        )

    db.assert_not_called()


@pytest.fixture
def active_dashboard(_db):
    now = utcnow()
    with get_db() as session:
        session.add(Dashboard(slug="audit-ko", title="T", first_author_email="a@b.c", created_at=now, updated_at=now))
    yield
    with get_db() as session:
        session.execute(delete(Dashboard).where(Dashboard.slug == "audit-ko"))


@pytest.mark.integration
@pytest.mark.usefixtures("active_dashboard")
def test_script_hosts_audit_lists_active_dashboard_pages_loading_a_forbidden_script(mocker):
    pages = {"audit-ko/index.html": ALLOWED_PAGE, "audit-ko/nice/index.html": OFFENDING_PAGE, "audit-ko/app.js": ""}
    mocker.patch.object(
        cron.s3.interactive,
        "list_files",
        side_effect=lambda prefix: [{"path": path} for path in pages if path.startswith(prefix)],
    )
    mocker.patch.object(cron.s3.interactive, "download", side_effect=lambda path: pages[path].encode())

    lines = cron.script_hosts_audit()

    assert lines[0].endswith("1 pages chargent un script hors des sites autorisés.")
    assert lines[1:] == [
        f"  {'audit-ko/nice/index.html':50s} https://gestaltfabrik.github.io/fluo-proto/static/vendor/jquery/jquery.min.js"
    ]
