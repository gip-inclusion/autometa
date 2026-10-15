"""Contrôle qualité des TDB — lib/viz_quality.py et le CLI du skill verify_dashboard."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from lib import viz_quality

_spec = importlib.util.spec_from_file_location(
    "verify_dashboard_cli", Path(__file__).parent.parent / "skills/verify_dashboard/scripts/verify_dashboard.py"
)
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)


def chart(**overrides) -> dict:
    return {"tag": "canvas", "id": "c", "width": 600, "height": 300, "painted": True, "broken": [], **overrides}


def layout(**overrides) -> dict:
    return {"overflow": 0, "text": "Visites 2026", "alerts": [], "generatedAt": "2026-09-18", **overrides}


def severities(issues: list[dict]) -> list[tuple[str, str]]:
    return [(i["check"], i["severity"]) for i in issues]


@pytest.mark.parametrize(
    "charts,expected,found",
    [
        ([chart()], 1, []),
        ([chart(width=0)], 0, [("chart", "error")]),
        ([chart(painted=False)], 0, [("chart", "error")]),
        ([chart(broken=["libellé undefined/NaN"])], 0, [("chart", "error")]),
        ([chart()], 2, [("chart", "error")]),
        ([], 0, [("chart", "warning")]),
    ],
    ids=["ok", "zero-size", "blank", "chartjs-broken", "missing-chart", "no-chart-expected"],
)
def test_chart_issues(charts, expected, found):
    assert severities(viz_quality.chart_issues(charts, expected)) == found


@pytest.mark.parametrize(
    "overrides,found",
    [
        ({}, []),
        ({"overflow": 240}, [("layout", "error")]),
        ({"text": "Taux : NaN %"}, [("error_text", "error")]),
        ({"alerts": ["Erreur : data.json introuvable"]}, [("error_text", "error")]),
        ({"text": "  "}, [("layout", "error")]),
        ({"generatedAt": "…"}, [("layout", "warning")]),
        ({"generatedAt": None}, []),
    ],
    ids=["ok", "overflow", "nan-text", "error-banner", "empty-page", "stale-footer", "no-footer"],
)
def test_layout_issues(overrides, found):
    assert severities(viz_quality.layout_issues(layout(**overrides))) == found


def test_visible_error_text_names_each_broken_value_once():
    issues = viz_quality.layout_issues(layout(text="undefined visites, NaN %, undefined"))

    assert issues[0]["message"].endswith("NaN, undefined")


def test_serve_exposes_the_dashboard_under_interactive_and_nothing_above_it(tmp_path):
    dashboard = tmp_path / "interactive" / "mon-tdb"
    dashboard.mkdir(parents=True)
    (dashboard / "index.html").write_text("<h1>TDB</h1>")
    (tmp_path / "secret.txt").write_text("hors du TDB")

    with viz_quality.serve(dashboard) as url:
        page = httpx.get(url, timeout=5)
        escape = httpx.get(url.replace("/interactive/mon-tdb/", "/interactive/%2E%2E/secret.txt"), timeout=5)

    assert (page.status_code, page.text) == (200, "<h1>TDB</h1>")
    assert escape.status_code == 404


class FakePage:
    def __init__(self):
        self.handlers = {}

    def on(self, event, handler):
        self.handlers[event] = handler


def request(url: str, resource_type: str = "script", failure: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(url=url, resource_type=resource_type, failure=failure)


def test_watch_records_console_page_and_network_errors_by_severity():
    page = FakePage()
    issues = viz_quality.watch(page)

    page.handlers["console"](SimpleNamespace(type="error", text="Chart is not defined"))
    page.handlers["console"](SimpleNamespace(type="error", text="Failed to load resource: 404"))
    page.handlers["console"](SimpleNamespace(type="warning", text="deprecated"))
    page.handlers["pageerror"](ValueError("render is not a function"))
    page.handlers["response"](SimpleNamespace(status=200, url="http://x/app.js", request=request("http://x/app.js")))
    page.handlers["response"](
        SimpleNamespace(status=500, url="http://x/api/query", request=request("http://x/api/query"))
    )
    page.handlers["response"](
        SimpleNamespace(status=404, url="http://x/data.json", request=request("http://x/data.json"))
    )
    page.handlers["requestfailed"](request("https://matomo.inclusion.beta.gouv.fr/matomo.js", failure="aborted"))
    page.handlers["requestfailed"](request("https://cdn/marianne.woff2", "font", "net::ERR_FAILED"))

    assert [(i["check"], i["severity"], i["message"]) for i in issues] == [
        ("console", "error", "Chart is not defined"),
        ("pageerror", "error", "render is not a function"),
        ("request", "warning", "http://x/api/query → HTTP 500 (non vérifiable hors application servie)"),
        ("request", "error", "script http://x/data.json → HTTP 404"),
        ("request", "warning", "font https://cdn/marianne.woff2 → net::ERR_FAILED"),
    ]


def test_audit_assembles_the_verdict_from_the_rendered_page(mocker, tmp_path):
    playwright = mocker.patch.object(viz_quality, "sync_playwright").return_value.__enter__.return_value
    page = playwright.chromium.launch.return_value.new_page.return_value
    page.wait_for_load_state.side_effect = viz_quality.PlaywrightTimeout("networkidle")
    page.evaluate.side_effect = [[chart(), chart(painted=False)], layout(generatedAt="…")]
    screenshot = tmp_path / "captures" / "tdb.png"

    result = viz_quality.audit("http://127.0.0.1:1/interactive/tdb/", screenshot, expected_charts=2)

    assert (result["passed"], result["charts"], result["screenshot"]) == (False, 2, str(screenshot))
    assert severities(result["issues"]) == [("chart", "error"), ("layout", "warning")]
    assert screenshot.parent.is_dir()
    page.screenshot.assert_called_once_with(path=screenshot, full_page=True)


def test_audit_passes_when_only_warnings_remain(mocker):
    playwright = mocker.patch.object(viz_quality, "sync_playwright").return_value.__enter__.return_value
    page = playwright.chromium.launch.return_value.new_page.return_value
    page.evaluate.side_effect = [[], layout()]

    result = viz_quality.audit("http://127.0.0.1:1/interactive/tdb/")

    assert (result["passed"], result["screenshot"], severities(result["issues"])) == (
        True,
        None,
        [("chart", "warning")],
    )
    page.screenshot.assert_not_called()


def test_verify_dashboard_serves_a_local_folder_to_the_audit(tmp_path, mocker):
    dashboard = tmp_path / "mon-tdb"
    dashboard.mkdir()
    (dashboard / "index.html").write_text("<h1>TDB</h1>")
    audit = mocker.patch.object(viz_quality, "audit", return_value={"passed": True})

    result = viz_quality.verify_dashboard(str(dashboard), expected_charts=1)

    url = audit.call_args.args[0]
    assert result == {"target": str(dashboard), "passed": True}
    assert url.startswith("http://127.0.0.1:") and url.endswith("/interactive/mon-tdb/")


def test_verify_dashboard_refuses_a_folder_without_index(tmp_path, mocker):
    mocker.patch.object(viz_quality.config, "INTERACTIVE_DIR", tmp_path)

    with pytest.raises(FileNotFoundError, match="index.html"):
        viz_quality.verify_dashboard("slug-inconnu")


def test_verify_dashboard_audits_a_url_without_serving_anything(mocker):
    audit = mocker.patch.object(viz_quality, "audit", return_value={"passed": True})
    serve = mocker.patch.object(viz_quality, "serve")

    result = viz_quality.verify_dashboard("http://127.0.0.1:5000/interactive/x/", expected_charts=2)

    assert result == {"target": "http://127.0.0.1:5000/interactive/x/", "passed": True}
    audit.assert_called_once_with("http://127.0.0.1:5000/interactive/x/", None, 2)
    serve.assert_not_called()


@pytest.mark.parametrize("passed,code", [(True, 0), (False, 1)], ids=["pass", "fail"])
def test_cli_prints_the_verdict_and_exits_on_it(passed, code, mocker, capsys, tmp_path):
    verify = mocker.patch.object(cli, "verify_dashboard", return_value={"passed": passed, "issues": []})
    mocker.patch("sys.argv", ["verify_dashboard.py", "mon-tdb", "--expect-charts", "3"])
    mocker.patch.object(cli.tempfile, "gettempdir", return_value=str(tmp_path))

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == code
    assert json.loads(capsys.readouterr().out)["passed"] is passed
    verify.assert_called_once_with("mon-tdb", tmp_path / "verify_dashboard" / "mon-tdb.png", 3)


@pytest.mark.parametrize(
    "error",
    [FileNotFoundError("Aucun index.html"), cli.PlaywrightError("Executable doesn't exist")],
    ids=["missing-dashboard", "missing-browser"],
)
def test_cli_exits_2_when_the_audit_cannot_run(error, mocker, capsys):
    mocker.patch.object(cli, "verify_dashboard", side_effect=error)
    mocker.patch("sys.argv", ["verify_dashboard.py", "mon-tdb"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 2
    assert "Error:" in capsys.readouterr().err
