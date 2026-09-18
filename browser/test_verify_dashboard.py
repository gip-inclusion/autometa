"""Le skill verify_dashboard rend un vrai TDB dans Chromium, sans application servie, et tranche entre sain et cassé."""

from pathlib import Path

import pytest

from lib.viz_quality import verify_dashboard

pytestmark = pytest.mark.browser

INDEX = """<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><link rel="stylesheet" href="style.css"></head>
<body>
  <h1>Visites mensuelles</h1>
  <div id="error" hidden class="error"></div>
  <canvas id="bars" width="400" height="200"></canvas>
  <svg id="line" width="400" height="200"></svg>
  <p id="kpi"></p>
  <footer><p>Données mises à jour le <span id="generated-at">…</span></p></footer>
  <script src="app.js"></script>
</body>
</html>"""

HEALTHY_APP = """
fetch('data.json').then(r => r.json()).then(data => {
  const ctx = document.getElementById('bars').getContext('2d');
  data.values.forEach((v, i) => ctx.fillRect(20 + i * 60, 200 - v * 20, 40, v * 20));
  const line = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
  line.setAttribute('points', data.values.map((v, i) => `${i * 60},${200 - v * 20}`).join(' '));
  line.setAttribute('stroke', 'navy');
  document.getElementById('line').append(line);
  document.getElementById('kpi').textContent = `Total : ${data.values.reduce((a, b) => a + b)}`;
  document.getElementById('generated-at').textContent = data.metadata.generated_at;
});
"""

BROKEN_APP = """
document.getElementById('kpi').textContent = `Taux : ${0 / 0} %`;
document.body.insertAdjacentHTML('beforeend', '<div style="width:3000px">tableau trop large</div>');
fetch('donnees.json').then(r => r.json()).then(data => render(data));
"""


def dashboard(root: Path, app_js: str) -> Path:
    directory = root / "interactive" / "tdb-test"
    directory.mkdir(parents=True)
    (directory / "index.html").write_text(INDEX)
    (directory / "style.css").write_text("body { font-family: sans-serif; }")
    (directory / "data.json").write_text('{"metadata": {"generated_at": "2026-09-18"}, "values": [3, 5, 2]}')
    (directory / "app.js").write_text(app_js)
    return directory


def test_a_healthy_dashboard_passes_with_its_charts_counted_and_a_screenshot(tmp_path):
    screenshot = tmp_path / "shot.png"

    result = verify_dashboard(str(dashboard(tmp_path, HEALTHY_APP)), screenshot, expected_charts=2)

    assert (result["passed"], result["charts"], result["issues"]) == (True, 2, [])
    assert screenshot.stat().st_size > 0


def test_a_broken_dashboard_fails_and_names_each_defect(tmp_path):
    result = verify_dashboard(str(dashboard(tmp_path, BROKEN_APP)), expected_charts=2)

    report = "\n".join(f"{i['severity']} {i['check']}: {i['message']}" for i in result["issues"])
    assert not result["passed"]
    assert "error request: fetch http" in report and "donnees.json → HTTP 404" in report
    assert "error error_text: valeurs cassées visibles dans la page : NaN" in report
    assert "error layout: débordement horizontal" in report
    assert "error chart: <canvas #bars> rendu vide" in report
    assert "error chart: <svg #line> rendu vide" in report
