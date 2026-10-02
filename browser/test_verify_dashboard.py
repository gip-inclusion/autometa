"""Vérification visuelle d'un tableau de bord, jouée dans Chromium sur des dossiers servis par le test lui-même."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from playwright.sync_api import Page

from lib.dashboard_quality import judge, observe, serve

pytestmark = pytest.mark.browser

REPO = Path(__file__).resolve().parent.parent

INDEX = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Candidatures</title>
    <link rel="stylesheet" href="style.css">
    <script async src="https://matomo.inclusion.beta.gouv.fr/js/container_TvNd7LvK.js"></script>
</head>
<body>
    <h1>Candidatures par mois</h1>
    <div id="error" hidden class="error"></div>
    <canvas id="evolution" width="600" height="300"></canvas>
    <footer>Données mises à jour le <span id="generated-at">…</span></footer>
    <script src="app.js"></script>
</body>
</html>"""

APP_JS = """async function init() {
    const data = await fetch('data.json').then(r => r.json());
    document.getElementById('generated-at').textContent = data.metadata.generated_at;
    const ctx = document.getElementById('evolution').getContext('2d');
    data.valeurs.forEach((v, i) => { ctx.fillStyle = '#000091'; ctx.fillRect(20 + i * 60, 300 - v, 40, v); });
}
init();"""

DATA = {"metadata": {"generated_at": "2026-09-18"}, "valeurs": [120, 150, 180]}


def make_dashboard(root: Path, app_js: str = APP_JS, data: dict | None = DATA) -> Path:
    directory = root / "interactive" / "candidatures"
    directory.mkdir(parents=True)
    (directory / "index.html").write_text(INDEX)
    (directory / "style.css").write_text("body { font-family: sans-serif; }")
    (directory / "app.js").write_text(app_js)
    if data is not None:
        (directory / "data.json").write_text(json.dumps(data))
    return directory


def errors_seen(page: Page, directory: Path, expected_charts: int = 0) -> list[str]:
    with serve(directory) as url:
        issues = judge(observe(page, url), expected_charts)
    return [i["message"] for i in issues if i["severity"] == "error"]


def test_dod_1_the_skill_passes_a_healthy_dashboard_without_autometa_running(tmp_path):
    directory = make_dashboard(tmp_path)

    run = subprocess.run(
        [sys.executable, "skills/verify_dashboard/scripts/verify_dashboard.py", str(directory), "--expect-charts", "1"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(run.stdout) == {"target": str(directory), "passed": True, "issues": []}


def test_dod_2_a_crashing_script_is_caught_with_its_message(page: Page, tmp_path):
    directory = make_dashboard(tmp_path, app_js=APP_JS.replace("data.valeurs", "data.valeurs_absentes"))

    assert any("forEach" in message for message in errors_seen(page, directory))


def test_dod_3_missing_data_is_named(page: Page, tmp_path):
    directory = make_dashboard(tmp_path, data=None)

    assert any("/interactive/candidatures/data.json" in message for message in errors_seen(page, directory))


def test_dod_4_a_blank_chart_is_caught(page: Page, tmp_path):
    directory = make_dashboard(tmp_path, app_js=APP_JS.replace("ctx.fillRect", "void"))

    assert any("canvas #evolution" in message for message in errors_seen(page, directory))


# Why: Chart.js et Plot viennent d'un CDN ; on reproduit ce qu'ils laissent dans la page pour tester hors réseau.
EMPTY_CHARTJS = APP_JS.replace(
    "init();",
    """window.Chart = {getChart: el => el.id === 'evolution' ? {data: {datasets: [{data: [null, NaN]}]}} : undefined};
init();""",
)

EMPTY_PLOT = """document.body.insertAdjacentHTML('beforeend', `<svg class="plot-d6a7b5" id="repartition" width="400" height="200">
  <g aria-label="x-axis tick"><path d="M0,0L400,0"></path></g>
  <g aria-label="y-axis tick label"><text>100</text></g>
  <g aria-label="bar"></g>
</svg>`);"""


@pytest.mark.parametrize(
    ("app_js", "blank"),
    [(EMPTY_CHARTJS, "canvas #evolution"), (APP_JS + EMPTY_PLOT, "svg #repartition")],
    ids=["chartjs", "plot"],
)
def test_dod_4_a_chart_library_drawing_only_its_axes_is_caught(page: Page, tmp_path, app_js, blank):
    directory = make_dashboard(tmp_path, app_js=app_js)

    assert any(blank in message for message in errors_seen(page, directory))


PLOT_LEGEND = """document.body.insertAdjacentHTML('beforeend', `<svg class="plot-d6a7b5-ramp" width="240" height="50">
  <image width="240" height="10" href="data:image/png;base64,iVBORw0KGgo="></image>
</svg>`);"""


def test_dod_13_a_plot_colour_legend_is_neither_a_chart_nor_an_empty_one(page: Page, tmp_path):
    directory = make_dashboard(tmp_path, app_js=APP_JS + PLOT_LEGEND)

    assert errors_seen(page, directory, expected_charts=1) == []
    assert errors_seen(page, directory, expected_charts=2) == ["1 graphique(s) affiché(s), 2 attendu(s)"]


def test_dod_8_the_tracking_script_is_blocked_and_not_reported(page: Page, tmp_path):
    directory = make_dashboard(tmp_path)
    blocked = []
    page.on("requestfailed", lambda request: blocked.append(request.url))

    assert errors_seen(page, directory, expected_charts=1) == []
    assert blocked == ["https://matomo.inclusion.beta.gouv.fr/js/container_TvNd7LvK.js"]
