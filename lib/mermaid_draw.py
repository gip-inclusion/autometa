"""Dessine en PNG, sur la sortie standard, le graphique Mermaid lu sur l'entrée : le processus enfant de mermaid_png."""

import sys

from playwright.sync_api import sync_playwright

# La version que charge la page (web/templates/base.html) : un graphique collé dans Slack est celui qu'elle montre.
MERMAID_URL = "https://cdn.jsdelivr.net/npm/mermaid@11.17.2/dist/mermaid.min.js"
PAGE = (
    "<!doctype html><meta charset='utf-8'><body style='margin:0;background:white'>"
    "<div id='chart' style='display:inline-block;padding:16px'></div>"
    f"<script src='{MERMAID_URL}'></script>"
)
DRAW = """async (source) => {
    mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'strict',
        theme: 'default',
        dompurifyConfig: {
            ALLOW_DATA_ATTR: false,
            FORBID_TAGS: ['style', 'img'],
            FORBID_ATTR: ['style', 'class', 'id', 'name'],
        },
    });
    const { svg } = await mermaid.render('drawn', source);
    document.getElementById('chart').innerHTML = svg;
}"""


def only_mermaid(route) -> None:
    """Laisse charger le script Mermaid et rien d'autre : le texte d'un graphique ne fait sortir aucune requête."""
    if route.request.url == MERMAID_URL:
        route.continue_()
    else:
        route.abort()


def draw(source: str) -> bytes:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 800}, device_scale_factor=2)
        page.route("**/*", only_mermaid)
        page.set_content(PAGE, wait_until="load", timeout=10_000)
        page.evaluate(DRAW, source)
        png = page.locator("#chart").screenshot(timeout=5_000)
        browser.close()
    return png


if __name__ == "__main__":
    sys.stdout.buffer.write(draw(sys.stdin.read()))
