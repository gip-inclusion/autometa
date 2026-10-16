"""Vérification visuelle d'un tableau de bord, jouée dans Chromium sur des dossiers servis par le test lui-même."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from playwright.sync_api import Page

from lib.dashboard_quality import judge, observe, serve

pytestmark = pytest.mark.browser

REPO = Path(__file__).resolve().parent.parent

# Why: les bibliothèques de graphiques documentées viennent d'un CDN ; leurs vraies versions sont servies hors réseau.
CDN = {"https://cdn.jsdelivr.net/npm/chart.js": "chart.umd.js", "https://cdn.jsdelivr.net/npm/d3@7": "d3.min.js"}
FIXTURES = Path(__file__).resolve().parent / "fixtures"

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

CHART_INDEX = INDEX.replace('    <canvas id="evolution" width="600" height="300"></canvas>\n', "").replace(
    '<script src="app.js">', "".join(f'<script src="{url}"></script>' for url in CDN) + '<script src="app.js">'
)


@pytest.fixture
def offline_libraries(page: Page) -> Page:
    page.route("https://cdn.jsdelivr.net/npm/**", lambda route: route.fulfill(path=FIXTURES / CDN[route.request.url]))
    return page


def make_dashboard(root: Path, app_js: str = APP_JS, data: dict | None = DATA, index: str = INDEX) -> Path:
    directory = root / "interactive" / "candidatures"
    directory.mkdir(parents=True)
    (directory / "index.html").write_text(index)
    (directory / "style.css").write_text("body { font-family: sans-serif; }")
    (directory / "app.js").write_text(app_js)
    if data is not None:
        (directory / "data.json").write_text(json.dumps(data))
    return directory


def errors_seen(page: Page, directory: Path, expected_charts: int = 0) -> list[str]:
    with serve(directory) as url:
        issues = judge(observe(page, url), expected_charts)
    return [i["message"] for i in issues if i["severity"] == "error"]


def run_skill(directory: Path, *args: str) -> dict:
    run = subprocess.run(
        [sys.executable, "skills/verify_dashboard/scripts/verify_dashboard.py", str(directory), *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    verdict = json.loads(run.stdout)
    assert run.returncode == (0 if verdict["passed"] else 1), run.stderr
    return verdict


def test_dod_1_the_skill_passes_a_healthy_dashboard_without_autometa_running(tmp_path):
    directory = make_dashboard(tmp_path)

    assert run_skill(directory, "--expect-charts", "1") == {"target": str(directory), "passed": True, "issues": []}


def test_dod_1_a_dashboard_built_on_the_official_template_passes(tmp_path):
    directory = tmp_path / "interactive" / "gabarit"
    shutil.copytree(REPO / "docs" / "dashboard-template", directory)
    (directory / "data.json").write_text(json.dumps({"metadata": {"generated_at": "2026-10-16"}, "candidatures": 1204}))

    assert run_skill(directory)["passed"] is True


def test_dod_2_a_crashing_script_is_caught_with_its_message(page: Page, tmp_path):
    directory = make_dashboard(tmp_path, app_js=APP_JS.replace("data.valeurs", "data.valeurs_absentes"))

    assert any("forEach" in message for message in errors_seen(page, directory))


def test_dod_3_missing_data_is_named(page: Page, tmp_path):
    directory = make_dashboard(tmp_path, data=None)

    assert any("/interactive/candidatures/data.json" in message for message in errors_seen(page, directory))


def test_dod_4_a_blank_chart_is_caught(page: Page, tmp_path):
    directory = make_dashboard(tmp_path, app_js=APP_JS.replace("ctx.fillRect", "void"))

    assert any("canvas #evolution" in message for message in errors_seen(page, directory))


def chartjs(config: str) -> str:
    return f"""const canvas = Object.assign(document.createElement('canvas'), {{id: 'evolution'}});
new Chart(document.body.appendChild(canvas), {config});"""


D3_AXES = """const svg = d3.select('body').append('svg').attr('id', 'repartition').attr('width', 400).attr('height', 200);
const x = d3.scaleBand().domain(['Paris', 'Lyon']).range([30, 390]);
const y = d3.scaleLinear().domain([0, 200]).range([180, 10]);
svg.append('g').attr('transform', 'translate(0,180)').call(d3.axisBottom(x));
svg.append('g').attr('transform', 'translate(30,0)').call(d3.axisLeft(y));
"""

D3_BARS = """svg.selectAll('rect').data([['Paris', 120], ['Lyon', 80]]).join('rect')
    .attr('x', d => x(d[0])).attr('width', x.bandwidth()).attr('y', d => y(d[1])).attr('height', d => 180 - y(d[1]));"""

# Why: Plot n'est pas servi hors réseau ; on reproduit le svg qu'il laisse quand ses marques sont vides.
EMPTY_PLOT = """document.body.insertAdjacentHTML('beforeend', `<svg class="plot-d6a7b5" id="repartition" width="400" height="200">
  <g aria-label="x-axis tick"><path d="M0,0L400,0"></path></g>
  <g aria-label="y-axis tick label"><text>100</text></g>
  <g aria-label="bar"></g>
</svg>`);"""


BLANK_CANVAS = "graphique canvas #evolution affiché sans aucun tracé"
BLANK_SVG = "graphique svg #repartition affiché sans aucun tracé"


@pytest.mark.parametrize(
    ("app_js", "errors"),
    [
        (chartjs("{type: 'bar', data: {labels: ['jan', 'fév'], datasets: [{data: [120, 150]}]}}"), []),
        (
            chartjs(
                "{type: 'bar', options: {indexAxis: 'y'},"
                " data: {datasets: [{data: [{x: 120, y: 'Paris'}, {x: 80, y: 'Lyon'}]}]}}"
            ),
            [],
        ),
        (
            chartjs(
                "{type: 'bar', options: {parsing: {xAxisKey: 'mois', yAxisKey: 'total'}},"
                " data: {datasets: [{data: [{mois: 'jan', total: 12}, {mois: 'fév', total: 30}]}]}}"
            ),
            [],
        ),
        (chartjs("{type: 'pie', data: {labels: ['a', 'b'], datasets: [{data: [3, 5]}]}}"), []),
        (chartjs("{type: 'bar', data: {labels: ['a', 'b'], datasets: [{data: [null, NaN]}]}}"), [BLANK_CANVAS]),
        (chartjs("{type: 'pie', data: {labels: ['a', 'b'], datasets: [{data: [null, NaN]}]}}"), [BLANK_CANVAS]),
        (D3_AXES + D3_BARS, []),
        (D3_AXES, [BLANK_SVG]),
        (EMPTY_PLOT, [BLANK_SVG]),
    ],
    ids=[
        "chartjs-vertical",
        "chartjs-horizontal",
        "chartjs-keyed",
        "chartjs-pie",
        "chartjs-null-nan",
        "chartjs-pie-null-nan",
        "d3-axes-and-bars",
        "d3-axes-only",
        "plot-axes-only",
    ],
)
def test_dod_4_a_chart_is_judged_by_what_its_library_drew(offline_libraries: Page, tmp_path, app_js, errors):
    directory = make_dashboard(tmp_path, app_js=app_js, index=CHART_INDEX)

    assert errors_seen(offline_libraries, directory) == errors


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
