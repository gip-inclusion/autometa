"""Preuves navigateur — le HTML qu'écrit un agent s'affiche sans jamais s'exécuter ni recouvrir la page."""

import json
import re
from collections.abc import Callable

import pytest
from playwright.sync_api import Page, Route, expect

pytestmark = [pytest.mark.browser, pytest.mark.usefixtures("fake_agent")]

PROBE = "window.probe = (name) => (window.__probes = window.__probes || []).push(name);"
MARKER = "/__untrusted-probe__"

# Why: chaque charge appelle probe() ou demande MARKER si elle agit ; les adresses en .invalid ne mènent nulle part.
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
    '<code class="position-fixed top-0 start-0 vw-100 vh-100 bg-white">Session expirée</code>',
    '<base href="https://example.invalid/">',
    f'<div data-hx-get="{MARKER}/answer" data-hx-trigger="load" hx-on:click="probe(\'htmx\')">htmx</div>',
    '<a href="https://example.org/" target="_top" id="probe-id" name="probe-name">cible</a>',
])

UNSAFE_MARKUP = """([region, allowed]) => {
  const found = document.querySelector('base') ? ['base'] : [];
  const tags = ['script', 'iframe', 'object', 'embed', 'form', 'style', 'svg', 'link', 'meta'];
  for (const root of document.querySelectorAll(region)) {
    if (!root.closest('[hx-disable]')) found.push('read by htmx');
    for (const el of root.querySelectorAll('*')) {
      const tag = el.tagName.toLowerCase();
      if (tags.includes(tag)) found.push(tag);
      for (const { name, value } of el.attributes) {
        if (allowed.includes(`${tag}[${name}]`)) continue;
        if (/^(on|data-|hx-)/.test(name) || ['style', 'srcdoc', 'id', 'name', 'target'].includes(name))
          found.push(`${tag}[${name}]`);
        if (name === 'class' && value && !(tag === 'code' && /^language-[\\w-]+$/.test(value))) found.push(`${tag}[class]`);
        if (/^\\s*javascript:/i.test(value)) found.push(`${tag}[${name}=javascript:]`);
      }
    }
  }
  return found;
}"""

ANSWERS = "#chatOutput .event-assistant"
TOC_IDS = ("h2[id]",)


def probes(page: Page) -> list[str]:
    return page.evaluate("() => window.__probes || []")


def marker_requests(page: Page) -> list[str]:
    """Les adresses MARKER que la page demande, à mesure qu'elles partent."""
    requested: list[str] = []

    def record(route: Route) -> None:
        requested.append(route.request.url)
        route.fulfill(body="")

    page.route(f"**{MARKER}/**", record)
    return requested


def assert_inert(page: Page, region: str, text: str, requested: list[str], allowed: tuple[str, ...] = ()) -> None:
    """`region` montre `text` et reste inerte : aucun balisage actif, aucune sonde déclenchée, aucune requête partie."""
    expect(page.locator(region).last).to_contain_text(text, timeout=15000)
    # Why: rien n'annonce qu'un gestionnaire ne s'exécutera pas ; on laisse aux erreurs d'image et aux animations
    # le temps de se déclencher.
    page.wait_for_timeout(1000)
    assert page.evaluate(UNSAFE_MARKUP, [region, list(allowed)]) == []
    assert probes(page) == []
    assert requested == []


def away_and_back(page: Page) -> None:
    page.locator('#nav-primary a[href="/conversations?show=convos"]').click()
    page.wait_for_url("**/conversations?show=convos")
    page.go_back()


def assert_stays_inert(page: Page, region: str, text: str, requested: list[str], allowed: tuple[str, ...] = ()) -> None:
    """Inerte une fois affichée, après un rechargement, puis au retour par Précédent qu'htmx restaure."""
    assert_inert(page, region, text, requested, allowed)
    page.reload(wait_until="domcontentloaded")
    assert_inert(page, region, text, requested, allowed)
    away_and_back(page)
    assert_inert(page, region, text, requested, allowed)


def with_stored_messages(page: Page, messages: list[dict]) -> None:
    """Ajoute des messages à l'historique que la page relit, comme si l'agent les avait écrits."""

    def extend(route: Route) -> None:
        response = route.fetch()
        conversation = response.json()
        route.fulfill(response=response, json={**conversation, "messages": conversation["messages"] + messages})

    page.route(re.compile(r"/api/conversations/[0-9a-f-]{36}$"), extend)


def test_an_answer_runs_none_of_its_html(page: Page, visit: Callable[[str], None], ask: Callable[[str], None]):
    page.add_init_script(PROBE)
    requested = marker_requests(page)
    visit("/explorations/new")
    ask(PAYLOADS)
    expect(page.locator(".event-final-answer")).to_have_count(1, timeout=15000)

    assert_stays_inert(page, ANSWERS, "Réponse factice", requested, TOC_IDS)
    answer = page.locator(".event-assistant").last
    answer.get_by_text("lien markdown").click()
    answer.get_by_text("lien html").click()
    assert probes(page) == []
    expect(page.locator("#chatInput")).to_be_visible()


def test_without_the_sanitizer_an_answer_is_plain_text(
    page: Page, visit: Callable[[str], None], ask: Callable[[str], None]
):
    page.add_init_script(PROBE)
    page.route("**/npm/dompurify@*/**", lambda route: route.abort())
    visit("/explorations/new")
    ask('<img src="x" onerror="probe(\'img\')">')
    assert_inert(page, ANSWERS, '<img src="x" onerror="probe(\'img\')">', [])
    expect(page.locator(ANSWERS).locator("img")).to_have_count(0)


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


def test_a_report_shows_its_header_and_body_without_running_them(conversation: str, page: Page):
    page.add_init_script(PROBE)
    requested = marker_requests(page)
    field = "<img src=x onerror=\"probe('report')\">"
    front_matter = f"query category: {field}\ndate: {field}\nwebsite: {field}"
    with_stored_messages(
        page,
        [
            {"id": 10**9, "type": "user", "content": "Un rapport ?"},
            {"id": 10**9 + 1, "type": "assistant", "content": f"---\n{front_matter}\n---\n{PAYLOADS}"},
        ],
    )
    page.reload(wait_until="domcontentloaded")
    header = page.locator(".report-header")
    expect(header).to_contain_text("<img src=x", timeout=15000)
    expect(header.locator("img")).to_have_count(0)

    assert_stays_inert(page, "#chatOutput .report-body", "Session expirée", requested, TOC_IDS)


@pytest.mark.parametrize(
    "message",
    [
        "[Uploaded file: note.txt]\n- Size: 12 bytes\n<img src=x onerror=\"probe('file')\">",
        "<img src=x onerror=\"probe('rule')\">\n---\nsuite",
    ],
)
def test_a_message_shows_its_html_as_text(
    page: Page, visit: Callable[[str], None], ask: Callable[[str], None], message
):
    page.add_init_script(PROBE)
    requested = marker_requests(page)
    visit("/explorations/new")
    ask(message)
    expect(page.locator(".event-assistant").last).to_contain_text("Réponse factice", timeout=15000)

    assert_stays_inert(page, "#chatOutput .event-user .user-text", "<img src=x", requested, ("a[target]",))
    expect(page.locator(".event-user").first.locator("img")).to_have_count(0)


def test_a_waiting_message_shows_its_html_as_text(conversation: str, page: Page, ask: Callable[[str], None]):
    page.add_init_script(PROBE)
    requested = marker_requests(page)
    page.reload(wait_until="domcontentloaded")
    ask("[hang] q0")
    expect(page.locator("#chatCancelBtn")).to_be_visible()
    page.locator("#chatInput").fill(PAYLOADS)
    page.locator("#chatInput").press("Enter")

    assert_stays_inert(page, "#chatQueue .user-text", "<img src=", requested, ("a[target]",))


def test_an_api_link_from_a_tool_output_keeps_only_a_web_address(conversation: str, page: Page):
    signal = {"source": "matomo", "method": "VisitsSummary.get", "url": "javascript:alert(1)"}
    with_stored_messages(
        page,
        [
            {"id": 10**9, "type": "tool_use", "content": json.dumps({"tool": "Bash", "input": {"command": "echo"}})},
            {"id": 10**9 + 1, "type": "tool_result", "content": json.dumps({"output": "x", "api_calls": [signal]})},
        ],
    )
    page.reload(wait_until="domcontentloaded")
    expect(page.locator(".action-api-link").first).to_contain_text("VisitsSummary.get", timeout=15000)
    links = "[...document.querySelectorAll('.action-api-link')]"
    assert set(page.evaluate(f"() => {links}.map((a) => a.getAttribute('href'))")) == {None}
    assert page.evaluate(f"() => {links}.every((a) => a.closest('[hx-disable]'))")


def with_knowledge_text(text: str) -> Callable[[Route], None]:
    """Remplace le texte d'une fiche de connaissance dans la page servie."""

    def replace(route: Route) -> None:
        response = route.fetch()
        body = re.sub(
            r'(<script id="knowledgeRawContent"[^>]*>).*?(</script>)',
            lambda match: match[1] + json.dumps(text).replace("<", "\\u003c") + match[2],
            response.text(),
            flags=re.DOTALL,
        )
        route.fulfill(response=response, body=body)

    return replace


@pytest.mark.parametrize("through_htmx", [False, True])
def test_a_knowledge_page_runs_none_of_its_html(page: Page, visit: Callable[[str], None], through_htmx: bool):
    page.add_init_script(PROBE)
    requested = marker_requests(page)
    page.route("**/knowledge/matomo/README.md", with_knowledge_text(f"**gras**\n\n{PAYLOADS}"))
    if through_htmx:
        visit("/knowledge")
        page.locator('a[href="/knowledge/matomo/README.md"]').click()
    else:
        visit("/knowledge/matomo/README.md")
    expect(page.locator("#markdownContent strong")).to_have_text("gras")

    assert_stays_inert(page, "#markdownContent", "Session expirée", requested)


def test_without_the_sanitizer_a_knowledge_page_is_plain_text(page: Page, visit: Callable[[str], None]):
    page.add_init_script(PROBE)
    page.route("**/npm/dompurify@*/**", lambda route: route.abort())
    page.route("**/knowledge/matomo/README.md", with_knowledge_text("<img src=x onerror=probe(1)> **gras**"))
    visit("/knowledge/matomo/README.md")
    expect(page.locator("#markdownContent strong")).to_have_text("gras")

    assert_inert(page, "#markdownContent", "<img src=x onerror=probe(1)>", [])
    expect(page.locator("#markdownContent img")).to_have_count(0)
