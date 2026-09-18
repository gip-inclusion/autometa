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

# Chart.js et Plot dessinent leurs axes même sans donnée : on juge leurs séries, pas leurs pixels. Un <svg> de
# 32 px au plus est un pictogramme, pas un graphique ; un élément masqué (onglet inactif) n'est pas jugé.
OBSERVE_JS = """() => {
  const shown = el => el !== null && el.checkVisibility() ? el.innerText.trim() : '';
  const value = v => (v !== null && typeof v === 'object' ? v.y : v);
  const painted = el => {
    if (el.tagName === 'svg' && [...el.classList].some(c => c.startsWith('plot'))) {
      return [...el.querySelectorAll('g[aria-label]')]
        .some(g => !/axis|grid|frame/.test(g.getAttribute('aria-label')) && g.childElementCount > 0);
    }
    if (el.tagName === 'svg') return el.querySelector('path, rect, circle, ellipse, line, polyline, polygon, text, image') !== null;
    const chart = window.Chart?.getChart?.(el);
    if (chart) return chart.data.datasets.some(d => (d.data ?? []).some(v => value(v) !== null && Number.isFinite(Number(value(v)))));
    if (!el.width || !el.height) return false;
    const ctx = el.getContext('2d');
    try {
      return ctx === null || ctx.getImageData(0, 0, el.width, el.height).data.some((v, i) => i % 4 === 3 && v > 0);
    } catch {
      return true;
    }
  };
  const charts = [...document.querySelectorAll('canvas, svg')]
    .filter(el => !el.parentElement.closest('svg') && el.checkVisibility())
    .map(el => {
      const {width, height} = el.getBoundingClientRect();
      return {name: el.tagName.toLowerCase() + (el.id ? ' #' + el.id : ''), width, height, painted: painted(el)};
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
    # Why: Chromium recopie en console chaque requête en échec, déjà relevée avec son adresse.
    if message.type == "error" and not message.text.startswith("Failed to load resource"):
        errors.append(message.text)


def on_response(failed: list[dict], response) -> None:
    if response.status >= 400:
        failed.append({"url": response.url, "reason": f"HTTP {response.status}"})


def on_request_failed(failed: list[dict], request) -> None:
    if urlsplit(request.url).hostname != TRACKING_HOST:
        failed.append({"url": request.url, "reason": request.failure})


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
            issues.append(issue(f"fichier non chargé : {failed['url']} ({failed['reason']})"))
    charts = observation["charts"]
    issues += [issue(f"graphique {c['name']} affiché sans aucun tracé") for c in charts if not c["painted"]]
    if len(charts) < expected_charts:
        issues.append(issue(f"{len(charts)} graphique(s) affiché(s), {expected_charts} attendu(s)"))
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
