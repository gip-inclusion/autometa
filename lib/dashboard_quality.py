"""Vérification visuelle d'un tableau de bord, rendu dans un navigateur sans écran avant d'en partager le lien."""

import logging
import re
import threading
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from web import config

logger = logging.getLogger(__name__)

# Why: le tag manager du gabarit compterait chaque vérification comme une visite réelle.
TRACKING_HOST = "matomo.inclusion.beta.gouv.fr"

BROKEN_VALUES = re.compile(r"\b(?:NaN|undefined|null)\b|\[object Object\]")

# Why: Chromium recopie en console chaque requête en échec ou refusée par CORS, déjà relevée avec son adresse.
NETWORK_ECHO = re.compile(r"^(?:Failed to load resource|Access to .+ blocked by CORS policy)")

# Une police, une image ou un média manquant dégrade l'aspect ; un script, un style ou data.json manquant casse le TDB.
COSMETIC_RESOURCES = {"font", "image", "media"}

# Chart.js, Plot et les axes D3 se dessinent même sans donnée : on juge les séries, pas les pixels. Chart.js : la valeur
# calculée sur l'axe des valeurs, quel que soit `indexAxis` ou `parsing` — une barre null n'est pas `skip`, et un
# camembert lit null comme 0, sans part. Un libellé absent est dessiné « undefined » dans le canvas, hors de tout
# texte de la page. Un graphique d'onglet inactif est compté et ses séries jugées, mais ni sa taille ni ses pixels :
# masqué, seuls ses attributs width/height en disent la taille. Ne sont pas des graphiques : un <svg> de 32 px au plus
# (pictogramme), la légende de couleur de Plot (`-ramp`).
OBSERVE_JS = """() => {
  const shown = el => el !== null && el.checkVisibility() ? el.innerText.trim() : '';
  const seriesDrawn = (chart, i) => {
    const meta = chart.getDatasetMeta(i);
    return meta.data.some((point, j) => {
      const parsed = meta.controller.getParsed(j);
      return !point.skip && (meta.vScale ? Number.isFinite(parsed[meta.vScale.axis]) : parsed > 0);
    });
  };
  const painted = el => {
    if (el.tagName === 'svg' && [...el.classList].some(c => c.startsWith('plot'))) {
      return [...el.querySelectorAll('g[aria-label]')]
        .some(g => !/axis|grid|frame/.test(g.getAttribute('aria-label')) && g.childElementCount > 0);
    }
    if (el.tagName === 'svg') {
      return el.querySelector(':is(path, rect, circle, ellipse, line, polyline, polygon, text, image):not(.tick *, .domain)') !== null;
    }
    if (!el.width || !el.height) return false;
    const ctx = el.getContext('2d');
    try {
      return ctx === null || ctx.getImageData(0, 0, el.width, el.height).data.some((v, i) => i % 4 === 3 && v > 0);
    } catch {
      return true;
    }
  };
  const charts = [...document.querySelectorAll('canvas, svg')]
    .filter(el => !el.parentElement.closest('svg'))
    .filter(el => ![...el.classList].some(c => c.endsWith('-ramp')))
    .map(el => {
      const visible = el.checkVisibility();
      const {width, height} = visible
        ? el.getBoundingClientRect()
        : {width: Number(el.getAttribute('width')) || 0, height: Number(el.getAttribute('height')) || 0};
      const name = el.tagName.toLowerCase() + (el.id ? ' #' + el.id : '');
      const chart = window.Chart?.getChart?.(el);
      if (!chart) return {name, width, height, painted: !visible || painted(el), empty_series: [], labels: []};
      const drawn = chart.data.datasets.map((_, i) => seriesDrawn(chart, i));
      const legend = chart.options.plugins?.legend?.display !== false ? chart.legend?.legendItems ?? [] : [];
      return {
        name,
        width,
        height,
        painted: drawn.includes(true),
        empty_series: drawn.includes(true)
          ? chart.data.datasets.flatMap((d, i) => (drawn[i] ? [] : [String(d.label ?? `n° ${i + 1}`)]))
          : [],
        labels: [...(chart.data.labels ?? []), ...legend.map(item => item.text)].map(String),
      };
    })
    .filter(c => c.name.startsWith('canvas') || c.width > 32 || c.height > 32);
  return {
    charts,
    text: document.body?.innerText ?? '',
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    error: shown(document.getElementById('error')),
    loading: shown(document.getElementById('loading')),
  };
}"""


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
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/interactive/{directory.name}/"
    finally:
        server.shutdown()
        server.server_close()


def on_console(errors: list[str], message) -> None:
    if message.type == "error" and not NETWORK_ECHO.match(message.text):
        errors.append(message.text)


def on_response(failed: list[dict], response) -> None:
    if response.status >= 400:
        failed.append({
            "url": response.url,
            "reason": f"HTTP {response.status}",
            "type": response.request.resource_type,
        })


def on_request_failed(failed: list[dict], request) -> None:
    if urlsplit(request.url).hostname != TRACKING_HOST:
        failed.append({"url": request.url, "reason": request.failure, "type": request.resource_type})


def observe(page: Page, url: str) -> dict:
    """Rend `url` dans `page` et relève ce qu'un utilisateur verrait."""
    observation = {"errors": [], "failed_requests": [], "timed_out": False}
    page.route(f"**://{TRACKING_HOST}/**", lambda route: route.abort())
    page.on("console", lambda message: on_console(observation["errors"], message))
    page.on("pageerror", lambda error: observation["errors"].append(str(error)))
    page.on("response", lambda response: on_response(observation["failed_requests"], response))
    page.on("requestfailed", lambda request: on_request_failed(observation["failed_requests"], request))
    try:
        page.goto(url, wait_until="networkidle", timeout=30_000)
    except PlaywrightTimeout:
        observation["timed_out"] = True
    return observation | page.evaluate(OBSERVE_JS)


def issue(message: str, severity: str = "error") -> dict:
    return {"severity": severity, "message": message}


def judge(observation: dict, expected_charts: int = 0) -> list[dict]:
    """Problèmes relevés dans une observation ; seuls ceux de sévérité `error` font échouer le verdict."""
    issues = [issue("délai dépassé : la page n'a pas fini de charger en 30 s")] if observation["timed_out"] else []
    issues += [issue(f"erreur JavaScript : {error}") for error in observation["errors"]]
    for failed in observation["failed_requests"]:
        if urlsplit(failed["url"]).path.startswith("/api/"):
            issues.append(issue(f"données en direct non vérifiées : {failed['url']}", "warning"))
        else:
            severity = "warning" if failed["type"] in COSMETIC_RESOURCES else "error"
            issues.append(issue(f"fichier non chargé : {failed['url']} ({failed['reason']})", severity))
    charts = observation["charts"]
    for c in charts:
        if not c["painted"]:
            issues.append(issue(f"graphique {c['name']} affiché sans aucun tracé"))
        issues += [issue(f"graphique {c['name']} : série « {s} » sans aucune valeur") for s in c["empty_series"]]
        issues += [
            issue(f"graphique {c['name']} : libellé cassé « {value} »")
            for value in sorted(set(BROKEN_VALUES.findall("\n".join(c["labels"]))))
        ]
    if len(charts) < expected_charts:
        issues.append(issue(f"{len(charts)} graphique(s) dans la page, {expected_charts} attendu(s)"))
    for value, count in Counter(BROKEN_VALUES.findall(observation["text"])).items():
        issues.append(issue(f"valeur cassée affichée : « {value} »" + (f" (×{count})" if count > 1 else "")))
    if observation["overflow"] > 1:
        issues.append(issue(f"le contenu déborde horizontalement de {observation['overflow']} px"))
    if not observation["text"].strip():
        issues.append(issue("la page n'affiche aucun texte"))
    if observation["error"]:
        issues.append(issue(f"bloc d'erreur affiché : {observation['error']}"))
    if observation["loading"]:
        issues.append(issue(f"« {observation['loading']} » encore affiché une fois la page chargée"))
    return issues


def verify(target: str, expected_charts: int = 0) -> dict:
    """Verdict sur le TDB désigné par son dossier ou son slug."""
    directory = Path(target) if Path(target).is_dir() else config.INTERACTIVE_DIR / target
    if not (directory / "index.html").is_file():
        issues = [issue("index.html introuvable")]
    else:
        with serve(directory.resolve()) as url, sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            issues = judge(observe(browser.new_page(), url), expected_charts)
            browser.close()
    return {"target": target, "passed": not any(i["severity"] == "error" for i in issues), "issues": issues}
