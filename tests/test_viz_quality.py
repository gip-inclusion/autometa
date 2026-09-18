"""Contrôle qualité des TDB — lib/viz_quality.py et le CLI du skill verify_dashboard."""

import importlib.util
import json
from pathlib import Path

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
