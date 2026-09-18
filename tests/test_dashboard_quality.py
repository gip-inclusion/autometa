"""Tests du verdict de qualité visuelle d'un tableau de bord (lib/dashboard_quality)."""

import json

import httpx
import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from lib import dashboard_quality
from lib.dashboard_quality import judge, observe, verify
from skills.verify_dashboard.scripts import verify_dashboard

PAGE_STATE = {"charts": [], "text": "x", "overflow": 0, "error": "", "loading": ""}


def make_observation(**overrides) -> dict:
    return {
        "errors": [],
        "failed_requests": [],
        "timed_out": False,
        "charts": [{"name": "canvas #evolution", "width": 600, "height": 300, "painted": True}],
        "text": "Candidatures par mois\n1 204 candidatures",
        "overflow": 0,
        "error": "",
        "loading": "",
        **overrides,
    }


def errors(issues: list[dict]) -> list[str]:
    return [i["message"] for i in issues if i["severity"] == "error"]


def test_dod_1_a_healthy_dashboard_has_no_issue():
    assert judge(make_observation(), expected_charts=1) == []


@pytest.mark.parametrize(
    "message",
    ["Uncaught TypeError: Cannot read properties of undefined (reading 'map')", "Erreur de chargement"],
)
def test_dod_2_a_javascript_error_fails_and_is_quoted(message):
    assert any(message in m for m in errors(judge(make_observation(errors=[message]))))


def test_dod_2_console_errors_are_kept_but_network_echoes_are_not(mocker):
    collected = []

    dashboard_quality.on_console(collected, mocker.Mock(type="error", text="boom"))
    dashboard_quality.on_console(collected, mocker.Mock(type="warning", text="dépréciée"))
    dashboard_quality.on_console(collected, mocker.Mock(type="error", text="Failed to load resource: 404 (Not Found)"))

    assert collected == ["boom"]


@pytest.mark.parametrize("url", ["http://127.0.0.1:1/interactive/tdb/data.json", "https://cdn.x/chart.js"])
def test_dod_3_a_missing_file_fails_and_is_named(url):
    issues = judge(make_observation(failed_requests=[{"url": url, "reason": "HTTP 404"}]))

    assert any(url in m for m in errors(issues))


def test_dod_3_failed_responses_and_requests_are_recorded(mocker):
    failed = []

    dashboard_quality.on_response(failed, mocker.Mock(url="http://h/data.json", status=404))
    dashboard_quality.on_response(failed, mocker.Mock(url="http://h/app.js", status=200))
    dashboard_quality.on_request_failed(failed, mocker.Mock(url="https://cdn.x/d3.js", failure="net::ERR_FAILED"))

    assert failed == [
        {"url": "http://h/data.json", "reason": "HTTP 404"},
        {"url": "https://cdn.x/d3.js", "reason": "net::ERR_FAILED"},
    ]


def test_dod_4_a_chart_without_any_mark_fails():
    blank = {"name": "canvas #vide", "width": 600, "height": 300, "painted": False}

    assert any("canvas #vide" in m for m in errors(judge(make_observation(charts=[blank]))))


def test_dod_4_fewer_charts_than_expected_fails():
    assert any("1 graphique(s) affiché(s), 3 attendu(s)" in m for m in errors(judge(make_observation(), 3)))


@pytest.mark.parametrize("value", ["NaN", "undefined", "null", "[object Object]"])
def test_dod_5_a_broken_value_on_screen_fails_and_is_quoted(value):
    issues = judge(make_observation(text=f"Taux d'embauche : {value} %"))

    assert any(f"« {value} »" in m for m in errors(issues))


def test_dod_6_horizontal_overflow_fails():
    assert any("déborde" in m for m in errors(judge(make_observation(overflow=240))))


def test_dod_6_a_page_without_text_fails():
    assert any("aucun texte" in m for m in errors(judge(make_observation(text="  \n "))))


def test_dod_8_the_tracking_script_is_never_a_problem(mocker):
    failed = []

    dashboard_quality.on_request_failed(
        failed, mocker.Mock(url="https://matomo.inclusion.beta.gouv.fr/js/container.js", failure="net::ERR_FAILED")
    )

    assert failed == []


def test_dod_9_live_data_is_a_warning_not_a_failure():
    live = {"url": "http://127.0.0.1:1/api/query", "reason": "HTTP 404"}

    issues = judge(make_observation(failed_requests=[live]))

    assert errors(issues) == []
    assert [i["message"] for i in issues] == ["données en direct non vérifiées : http://127.0.0.1:1/api/query"]


@pytest.mark.parametrize(
    ("overrides", "quoted"),
    [
        ({"error": "Impossible de contacter le serveur"}, "Impossible de contacter le serveur"),
        ({"loading": "Chargement…"}, "Chargement…"),
    ],
)
def test_dod_10_an_error_block_or_a_stuck_loader_fails(overrides, quoted):
    assert any(quoted in m for m in errors(judge(make_observation(**overrides))))


def test_dod_11_a_dashboard_without_index_fails_without_crashing(tmp_path):
    assert verify(str(tmp_path)) == {
        "target": str(tmp_path),
        "passed": False,
        "issues": [{"severity": "error", "message": "index.html introuvable"}],
    }


def test_dod_11_an_unknown_slug_is_looked_up_in_the_dashboards_folder(tmp_path, mocker):
    mocker.patch.object(dashboard_quality.config, "INTERACTIVE_DIR", tmp_path)

    assert verify("inconnu")["issues"] == [{"severity": "error", "message": "index.html introuvable"}]


def test_dod_12_a_page_still_loading_after_the_delay_fails():
    assert any("délai dépassé" in m for m in errors(judge(make_observation(timed_out=True))))


def test_dod_12_observe_reports_a_timeout_instead_of_raising(mocker):
    page = mocker.MagicMock()
    page.goto.side_effect = PlaywrightTimeout("30000ms exceeded")
    page.evaluate.return_value = PAGE_STATE

    observation = observe(page, "http://127.0.0.1:1/interactive/tdb/")

    assert observation["timed_out"] is True
    page.goto.assert_called_once_with("http://127.0.0.1:1/interactive/tdb/", wait_until="networkidle", timeout=30_000)


def test_dod_13_no_chart_expected_means_no_minimum():
    assert judge(make_observation(charts=[])) == []


@pytest.mark.parametrize("text", ["Taux de nullité : 3 %", "Undefined behaviour", "NaNterre", "nullement"])
def test_dod_13_broken_values_are_whole_words_only(text):
    assert judge(make_observation(text=text)) == []


def test_dod_13_a_repeated_broken_value_is_reported_once_with_its_count():
    issues = judge(make_observation(text="NaN\nNaN\nNaN"))

    assert errors(issues) == ["valeur cassée affichée : « NaN » (×3)"]


def test_observe_blocks_tracking_and_merges_what_the_page_shows(mocker):
    page = mocker.MagicMock()
    page.evaluate.return_value = PAGE_STATE

    observation = observe(page, "http://127.0.0.1:1/interactive/tdb/")

    page.route.assert_called_once()
    assert observation == make_observation(charts=[], text="x")


def test_verify_serves_the_dashboard_folder_and_judges_it(tmp_path, mocker):
    (tmp_path / "tdb").mkdir()
    (tmp_path / "tdb" / "index.html").write_text("<h1>Mon TDB</h1>")
    mocker.patch.object(dashboard_quality, "sync_playwright")
    served = {}

    def fake_observe(page, url):
        served["index"] = httpx.get(url, timeout=5).text
        served["api"] = httpx.get(url.replace("/interactive/tdb/", "/api/query"), timeout=5).status_code
        return make_observation()

    mocker.patch.object(dashboard_quality, "observe", side_effect=fake_observe)

    result = verify(str(tmp_path / "tdb"), expected_charts=1)

    assert result == {"target": str(tmp_path / "tdb"), "passed": True, "issues": []}
    assert served == {"index": "<h1>Mon TDB</h1>", "api": 404}


@pytest.mark.parametrize(("passed", "exit_code"), [(True, 0), (False, 1)])
def test_dod_1_the_command_prints_the_verdict_and_exits_on_it(mocker, capsys, passed, exit_code):
    result = {"target": "mon-tdb", "passed": passed, "issues": []}
    verify_mock = mocker.patch.object(verify_dashboard, "verify", return_value=result)
    mocker.patch("sys.argv", ["verify_dashboard.py", "mon-tdb", "--expect-charts", "2"])

    with pytest.raises(SystemExit) as exit_info:
        verify_dashboard.main()

    assert exit_info.value.code == exit_code
    assert json.loads(capsys.readouterr().out) == result
    verify_mock.assert_called_once_with("mon-tdb", 2)
