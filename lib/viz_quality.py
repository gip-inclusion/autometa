"""Contrôle qualité d'un tableau de bord rendu dans un Chromium headless (Playwright)."""

import logging
import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from web import config

logger = logging.getLogger(__name__)

# Why: le tag manager inclus dans le gabarit compterait chaque audit comme une visite réelle.
TRACKING_HOST = "matomo.inclusion.beta.gouv.fr"

# Why: le navigateur recopie en console chaque échec réseau, déjà relevé avec sa sévérité par watch().
NETWORK_CONSOLE = re.compile(r"^(Failed to load resource|Access to .+ blocked by CORS policy)")

# Une police ou une image manquante dégrade l'aspect ; un script, un style ou data.json manquant casse le TDB.
COSMETIC_RESOURCES = {"font", "image", "media"}

VISIBLE_ERRORS = re.compile(r"\bundefined\b|\bNaN\b|\[object Object\]|Traceback \(most recent call last\)")

# Un <svg> de 32 px au plus est un pictogramme, pas un graphique.
CHARTS_JS = """() => [...document.querySelectorAll('canvas, svg')]
  .filter(el => !el.parentElement.closest('svg') && el.checkVisibility())
  .map(el => {
    const {width, height} = el.getBoundingClientRect();
    let painted = true;
    if (el.tagName === 'CANVAS') {
      const ctx = el.width && el.height ? el.getContext('2d', {willReadFrequently: true}) : null;
      if (ctx) painted = ctx.getImageData(0, 0, el.width, el.height).data.some((v, i) => i % 4 === 3 && v > 0);
      else painted = !!el.width && !!el.height && !!(el.getContext('webgl2') || el.getContext('webgl'));
    } else {
      painted = el.querySelector('path, rect, circle, ellipse, line, polyline, polygon, text, image') !== null;
    }
    const chart = el.tagName === 'CANVAS' ? window.Chart?.getChart?.(el) : undefined;
    const broken = [];
    if (chart) {
      const value = v => (v !== null && typeof v === 'object' ? v.y : v);
      const legend = chart.options.plugins?.legend?.display !== false;
      const labels = [...(chart.data.labels ?? []), ...chart.data.datasets.map(d => (legend ? d.label : ''))];
      if (labels.some(l => /^(undefined|NaN|null)$/.test(String(l)))) broken.push('libellé undefined/NaN');
      chart.data.datasets
        .filter(d => !(d.data ?? []).some(v => Number.isFinite(Number(value(v))) && value(v) !== null))
        .forEach(d => broken.push(`série « ${d.label ?? '?'} » sans aucune valeur`));
    }
    return {tag: el.tagName.toLowerCase(), id: el.id, width, height, painted, broken};
  })
  .filter(c => !(c.tag === 'svg' && c.width * c.height > 0 && c.width <= 32 && c.height <= 32))"""

LAYOUT_JS = """() => ({
  overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  text: document.body.innerText,
  alerts: [...document.querySelectorAll('#error, .error, [role="alert"]')]
    .filter(el => el.checkVisibility() && el.innerText.trim())
    .map(el => el.innerText.trim()),
  generatedAt: document.getElementById('generated-at')?.innerText.trim() ?? null,
})"""


class DashboardHandler(SimpleHTTPRequestHandler):
    """Sert le dossier du TDB sous les mêmes préfixes que l'application : `/interactive/` et `/common/`."""

    def translate_path(self, path: str) -> str:
        route = unquote(urlsplit(path).path)
        for prefix, root in self.server.roots.items():
            candidate = (root / route.removeprefix(prefix)).resolve()
            if route.startswith(prefix) and candidate.is_relative_to(root.resolve()):
                return str(candidate)
        return ""

    def log_message(self, format: str, *args) -> None:
        logger.debug(format, *args)


@contextmanager
def serve(directory: Path) -> Iterator[str]:
    """URL locale du TDB, servi le temps du bloc."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
    server.roots = {"/interactive/": directory.parent, "/common/": config.COMMON_DIR}
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/interactive/{directory.name}/"
    finally:
        server.shutdown()
        server.server_close()


def issue(check: str, message: str, severity: str = "error") -> dict:
    return {"check": check, "severity": severity, "message": message}


def request_issue(request, reason: str) -> dict:
    severity = "warning" if request.resource_type in COSMETIC_RESOURCES else "error"
    return issue("request", f"{request.resource_type} {request.url} → {reason}", severity)


def watch(page: Page) -> list[dict]:
    """Journalise erreurs console, exceptions JS et requêtes en échec pendant le rendu."""
    issues = []

    def on_console(message):
        if message.type == "error" and not NETWORK_CONSOLE.match(message.text):
            issues.append(issue("console", message.text))

    def on_response(response):
        if response.status < 400:
            return
        if urlsplit(response.url).path.startswith("/api/"):
            message = f"{response.url} → HTTP {response.status} (non vérifiable hors application servie)"
            issues.append(issue("request", message, "warning"))
        else:
            issues.append(request_issue(response.request, f"HTTP {response.status}"))

    def on_failed(request):
        if urlsplit(request.url).hostname != TRACKING_HOST:
            issues.append(request_issue(request, request.failure))

    page.on("console", on_console)
    page.on("pageerror", lambda error: issues.append(issue("pageerror", str(error))))
    page.on("response", on_response)
    page.on("requestfailed", on_failed)
    return issues


def chart_issues(charts: list[dict], expected: int) -> list[dict]:
    issues = []
    for chart in charts:
        name = f"<{chart['tag']}{' #' + chart['id'] if chart['id'] else ''}>"
        if chart["width"] < 2 or chart["height"] < 2:
            issues.append(
                issue("chart", f"{name} visible mais de taille nulle ({chart['width']:.0f}×{chart['height']:.0f})")
            )
        elif not chart["painted"]:
            issues.append(issue("chart", f"{name} rendu vide : aucun tracé"))
        issues += [issue("chart", f"{name} Chart.js : {problem}") for problem in chart["broken"]]
    if len(charts) < expected:
        issues.append(issue("chart", f"{len(charts)} graphique(s) rendu(s), {expected} attendu(s)"))
    elif not charts:
        issues.append(issue("chart", "aucun graphique détecté", "warning"))
    return issues


def layout_issues(layout: dict) -> list[dict]:
    issues = [issue("error_text", f"message d'erreur affiché : {alert}") for alert in layout["alerts"]]
    if layout["overflow"] > 1:
        issues.append(issue("layout", f"débordement horizontal de {layout['overflow']} px"))
    if found := sorted(set(VISIBLE_ERRORS.findall(layout["text"]))):
        issues.append(issue("error_text", f"valeurs cassées visibles dans la page : {', '.join(found)}"))
    if not layout["text"].strip():
        issues.append(issue("layout", "page sans aucun texte visible"))
    if layout["generatedAt"] in ("", "…"):
        issues.append(issue("layout", "date de fraîcheur (#generated-at) non renseignée", "warning"))
    return issues


def audit(url: str, screenshot: Path | None = None, expected_charts: int = 0) -> dict:
    """Rend `url` en headless et renvoie le verdict ; seules les issues `error` le font échouer."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.route(f"**://{TRACKING_HOST}/**", lambda route: route.abort())
        issues = watch(page)
        page.goto(url, wait_until="load", timeout=30_000)
        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except PlaywrightTimeout:
            logger.warning("Réseau jamais au repos sur %s, audit sur l'état courant", url)
        # Why: laisse finir une éventuelle animation initiale de Chart.js avant de lire les pixels.
        page.wait_for_timeout(1_000)
        charts = page.evaluate(CHARTS_JS)
        issues += chart_issues(charts, expected_charts) + layout_issues(page.evaluate(LAYOUT_JS))
        if screenshot:
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=screenshot, full_page=True)
        browser.close()
    return {
        "url": url,
        "passed": not any(i["severity"] == "error" for i in issues),
        "charts": len(charts),
        "screenshot": str(screenshot) if screenshot else None,
        "issues": issues,
    }


def verify_dashboard(target: str, screenshot: Path | None = None, expected_charts: int = 0) -> dict:
    """Audite un TDB désigné par son slug, son dossier ou son URL."""
    if urlsplit(target).scheme in ("http", "https"):
        return {"target": target, **audit(target, screenshot, expected_charts)}
    directory = Path(target) if Path(target).is_dir() else config.INTERACTIVE_DIR / target
    if not (directory / "index.html").is_file():
        raise FileNotFoundError(f"Aucun index.html dans {directory}")
    with serve(directory.resolve()) as url:
        return {"target": target, **audit(url, screenshot, expected_charts)}
