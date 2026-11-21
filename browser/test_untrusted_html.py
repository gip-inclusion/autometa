"""Preuves navigateur — le HTML qu'écrit un agent s'affiche sans jamais s'exécuter ni recouvrir la page."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.browser, pytest.mark.usefixtures("fake_agent")]

PROBE = "window.probe = (name) => (window.__probes = window.__probes || []).push(name);"

# Why: chaque charge appelle probe() si elle s'exécute ; les adresses en .invalid ne mènent nulle part.
PAYLOADS = "\n\n".join([
    '<img src="x" onerror="probe(\'img\')">',
    "<details open ontoggle=\"probe('details')\"><summary>Résumé</summary>Détail</details>",
    "[lien markdown](javascript:probe('markdown-link'))",
    "<a href=\"javascript:probe('html-link')\">lien html</a>",
    "<script>probe('script')</script>",
    "<iframe srcdoc=\"&lt;script&gt;parent.probe('iframe')&lt;/script&gt;\"></iframe>",
    '<object data="https://example.invalid/"></object>',
    '<form action="https://example.invalid/"><input name="q"><button>Envoyer</button></form>',
    '<svg><animate attributeName="x" dur="1s" onbegin="probe(\'svg\')"/></svg>',
    "<style>.chat-input { display: none }</style>",
    '<div style="position: fixed; inset: 0; z-index: 9999; background: #fff">Session expirée</div>',
    '<div class="position-fixed top-0 start-0 vw-100 vh-100 bg-white">Session expirée</div>',
    '<base href="https://example.invalid/">',
])

UNSAFE_MARKUP = """() => {
  const found = document.querySelector('base') ? ['base'] : [];
  for (const el of document.querySelectorAll('#chatOutput .event-assistant *')) {
    const tag = el.tagName.toLowerCase();
    if (['script', 'iframe', 'object', 'embed', 'form', 'style', 'svg', 'link', 'meta'].includes(tag)) found.push(tag);
    for (const { name, value } of el.attributes) {
      if (name.startsWith('on') || name === 'style' || name === 'srcdoc') found.push(`${tag}[${name}]`);
      if (name === 'class' && tag !== 'code') found.push(`${tag}[class]`);
      if (/^\\s*javascript:/i.test(value)) found.push(`${tag}[${name}=javascript:]`);
    }
  }
  return found;
}"""


def answer_shown(page: Page) -> None:
    expect(page.locator(".event-assistant").last).to_contain_text("Réponse factice", timeout=15000)
    # Why: rien n'annonce qu'un gestionnaire ne s'exécutera pas ; on laisse aux erreurs d'image et aux animations
    # le temps de se déclencher.
    page.wait_for_timeout(1000)


def probes(page: Page) -> list[str]:
    return page.evaluate("() => window.__probes || []")


def test_an_answer_runs_none_of_its_html(page: Page, visit: Callable[[str], None], ask: Callable[[str], None]):
    page.add_init_script(PROBE)
    visit("/explorations/new")
    ask(PAYLOADS)
    expect(page.locator(".event-final-answer")).to_have_count(1, timeout=15000)
    answer_shown(page)
    assert probes(page) == []
    assert page.evaluate(UNSAFE_MARKUP) == []
    expect(page.locator("#chatInput")).to_be_visible()
    page.locator(".event-assistant").get_by_text("lien markdown").click()
    page.locator(".event-assistant").get_by_text("lien html").click()
    assert probes(page) == []

    page.reload(wait_until="domcontentloaded")
    answer_shown(page)
    assert probes(page) == []
    assert page.evaluate(UNSAFE_MARKUP) == []

    page.locator('#nav-primary a[href="/conversations?show=convos"]').click()
    page.wait_for_url("**/conversations?show=convos")
    page.go_back()
    answer_shown(page)
    assert probes(page) == []


def test_without_the_sanitizer_an_answer_is_plain_text(
    page: Page, visit: Callable[[str], None], ask: Callable[[str], None]
):
    page.add_init_script(PROBE)
    page.route("**/npm/dompurify@*/**", lambda route: route.abort())
    visit("/explorations/new")
    ask('<img src="x" onerror="probe(\'img\')">')
    answer_shown(page)
    answer = page.locator(".event-assistant").last
    expect(answer).to_contain_text('<img src="x" onerror="probe(\'img\')">')
    expect(answer.locator("img")).to_have_count(0)
    assert probes(page) == []


def test_a_rich_answer_keeps_its_formatting(page: Page, visit: Callable[[str], None], ask: Callable[[str], None]):
    visit("/explorations/new")
    ask(
        "\n\n".join([
            "Bilan",
            "| Colonne | Valeur |\n|---|---|\n| a | ligne 1<br>ligne 2 |",
            "```python\nprint(1)\n```",
            "[Documentation](https://example.org/doc)",
            "<details><summary>Plus</summary>Détail caché</details>",
            "H<sub>2</sub>O et 10<sup>3</sup>",
            "```mermaid\ngraph TD\n  A --> B\n```",
            "```options\nOui\nNon | Non merci\n```",
        ])
    )
    expect(page.locator(".event-final-answer")).to_have_count(1, timeout=15000)
    answer = page.locator(".event-assistant").last
    expect(answer.locator(".mermaid svg .node")).to_have_count(2)
    for selector, count in [
        ("table td br", 1),
        ("pre code.language-python", 1),
        ('a[href="https://example.org/doc"]', 1),
        ("details summary", 1),
        ("sub", 1),
        ("sup", 1),
        (".options-buttons button", 2),
    ]:
        expect(answer.locator(selector)).to_have_count(count)
