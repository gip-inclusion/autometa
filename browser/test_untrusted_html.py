"""Preuves navigateur — le HTML qu'écrit un agent s'affiche sans jamais s'exécuter ni recouvrir la page."""

import json
import re
from collections.abc import Callable, Iterator

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
    '<input type="text" placeholder="Mot de passe"> <input type="checkbox">',
    "<dialog open>Fenêtre</dialog> <marquee>Défilant</marquee> <label>Étiquette</label>",
])

# Why: Mermaid nettoie lui-même les étiquettes qu'il dessine ; un déclencheur différé attend qu'htmx relise la page
# restaurée par Précédent. Les deux derniers graphiques tentent d'assouplir ce nettoyage.
LABEL = (
    f"<span data-hx-get='{MARKER}/chart' data-hx-trigger='load delay:300ms' data-hx-on--trigger='probe(1)' "
    f"data-hx-on-mouseover='probe(2)'>Étape</span><img src='{MARKER}/image'>"
)
DIAGRAMS = [
    f'flowchart TD\n  A["{LABEL}"] -->|"{LABEL}"| B',
    f'classDiagram\n  class A["{LABEL}"]',
    f"stateDiagram-v2\n  s1 : {LABEL}",
    f'erDiagram\n  A ||--o{{ B : "{LABEL}"',
    f'block-beta\n  a["{LABEL}"]',
    f'%%{{init: {{"securityLevel": "loose", "dompurifyConfig": {{"ALLOW_DATA_ATTR": true}}}}}}%%\nflowchart TD\n  A["{LABEL}"]',
    f'---\nconfig:\n  dompurifyConfig:\n    ALLOW_DATA_ATTR: true\n---\nflowchart TD\n  A["{LABEL}"]',
]
CHARTS = "\n\n".join(f"```mermaid\n{code}\n```" for code in DIAGRAMS)

OVERLAY = (
    '<h2 popover="manual">Session expirée</h2>\n\n'
    '<button popovertarget="session-expiree" popovertargetaction="show">Afficher le tableau</button> '
    '<button commandfor="session-expiree" command="show-popover">Voir le détail</button>'
)

# Why: sans createHTMLDocument, DOMPurify se déclare incapable de tourner et rend son entrée telle quelle.
UNSUPPORTED = "Object.defineProperty(DOMImplementation.prototype, 'createHTMLDocument', { value: undefined });"

# Why: Mermaid dessine son propre SVG (classes, styles, identifiants) ; dans un graphique, seuls les attributs qu'htmx ou
# le navigateur exécuteraient sont jugés.
UNSAFE_MARKUP = """([region, allowed]) => {
  const found = document.querySelector('base') ? ['base'] : [];
  const tags = ['script', 'iframe', 'object', 'embed', 'form', 'style', 'svg', 'link', 'meta', 'dialog', 'button',
    'select', 'textarea', 'option', 'datalist', 'fieldset', 'legend', 'output', 'label', 'marquee'];
  for (const root of document.querySelectorAll(region)) {
    if (!root.closest('[hx-disable]')) found.push('read by htmx');
    for (const el of root.querySelectorAll('*')) {
      const tag = el.tagName.toLowerCase();
      if (el.closest('.mermaid')) {
        for (const { name } of el.attributes) if (/^(on|hx-|data-hx-)/.test(name)) found.push(`chart ${tag}[${name}]`);
        continue;
      }
      if (tags.includes(tag)) found.push(tag);
      if (tag === 'input' && !(el.type === 'checkbox' && el.disabled)) found.push('input');
      for (const { name, value } of el.attributes) {
        if (allowed.includes(`${tag}[${name}]`)) continue;
        if (/^(on|data-|hx-|popover|command)/.test(name) || ['style', 'srcdoc', 'id', 'name', 'target'].includes(name))
          found.push(`${tag}[${name}]`);
        if (name === 'class' && value && !(tag === 'code' && /^language-[\\w-]+$/.test(value))) found.push(`${tag}[class]`);
        if (/^\\s*javascript:/i.test(value)) found.push(`${tag}[${name}=javascript:]`);
      }
    }
  }
  return found;
}"""

HOVER_CHARTS = """() => document.querySelectorAll('.mermaid *')
  .forEach((el) => el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true })))"""

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


def assert_inert(
    page: Page, region: str, text: str, requested: list[str], allowed: tuple[str, ...] = (), charts: int = 0
) -> None:
    """`region` montre `text` et reste inerte : aucun balisage actif, aucune sonde déclenchée, aucune requête partie."""
    expect(page.locator(region).last).to_contain_text(text, timeout=15000)
    expect(page.locator(f"{region} .mermaid svg")).to_have_count(charts)
    page.evaluate(HOVER_CHARTS)
    # Why: rien n'annonce qu'un gestionnaire ne s'exécutera pas ; une seconde dépasse tout délai des charges (300 ms).
    page.wait_for_timeout(1000)
    assert page.evaluate(UNSAFE_MARKUP, [region, list(allowed)]) == []
    assert probes(page) == []
    assert requested == []


def away_and_back(page: Page) -> None:
    page.locator('#nav-primary a[href="/conversations?show=convos"]').click()
    page.wait_for_url("**/conversations?show=convos")
    page.go_back()


def assert_stays_inert(
    page: Page, region: str, text: str, requested: list[str], allowed: tuple[str, ...] = (), charts: int = 0
) -> None:
    """Inerte une fois affichée, après un rechargement, puis au retour par Précédent qu'htmx restaure."""
    assert_inert(page, region, text, requested, allowed, charts)
    page.reload(wait_until="domcontentloaded")
    assert_inert(page, region, text, requested, allowed, charts)
    away_and_back(page)
    assert_inert(page, region, text, requested, allowed, charts)


def with_stored_messages(page: Page, messages: list[dict]) -> None:
    """Ajoute des messages à l'historique que la page relit, comme si l'agent les avait écrits."""

    def extend(route: Route) -> None:
        response = route.fetch()
        conversation = response.json()
        route.fulfill(response=response, json={**conversation, "messages": conversation["messages"] + messages})

    page.route(re.compile(r"/api/conversations/(?:[0-9a-f-]{36}|[0-9a-z]{8})$"), extend)


def test_an_answer_runs_none_of_its_html(page: Page, visit: Callable[[str], None], ask: Callable[[str], None]):
    page.add_init_script(PROBE)
    requested = marker_requests(page)
    visit("/c/new")
    ask(PAYLOADS)
    expect(page.locator(".event-final-answer")).to_have_count(1, timeout=15000)

    assert_stays_inert(page, ANSWERS, "Réponse factice", requested, TOC_IDS)
    answer = page.locator(".event-assistant").last
    answer.get_by_text("lien markdown").click()
    answer.get_by_text("lien html").click()
    assert probes(page) == []
    expect(page.locator("#chatInput")).to_be_visible()


def test_a_chart_label_runs_nothing(page: Page, visit: Callable[[str], None], ask: Callable[[str], None]):
    page.add_init_script(PROBE)
    requested = marker_requests(page)
    visit("/c/new")
    ask(f"Graphiques\n\n{CHARTS}")

    assert_stays_inert(page, ANSWERS, "Réponse factice", requested, TOC_IDS, charts=len(DIAGRAMS))


def test_an_answer_cannot_open_an_overlay(page: Page, visit: Callable[[str], None], ask: Callable[[str], None]):
    requested = marker_requests(page)
    visit("/c/new")
    ask(OVERLAY)
    assert_inert(page, ANSWERS, "Afficher le tableau", requested, TOC_IDS)
    answer = page.locator(".event-assistant").last

    answer.get_by_text("Afficher le tableau").click()
    answer.get_by_text("Voir le détail").click()

    assert page.evaluate("() => document.querySelectorAll(':popover-open').length") == 0
    expect(answer.locator("h2")).to_be_visible()


@pytest.mark.parametrize("sanitizer", ["missing", "unsupported"])
def test_without_the_sanitizer_an_answer_is_plain_text(
    page: Page, visit: Callable[[str], None], ask: Callable[[str], None], sanitizer: str
):
    page.add_init_script(PROBE)
    if sanitizer == "missing":
        page.route("**/npm/dompurify@*/**", lambda route: route.abort())
    else:
        page.add_init_script(UNSUPPORTED)
    visit("/c/new")
    ask('<img src="x" onerror="probe(\'img\')">')
    assert_inert(page, ANSWERS, '<img src="x" onerror="probe(\'img\')">', [])
    expect(page.locator(ANSWERS).locator("img")).to_have_count(0)


def test_a_rich_answer_keeps_its_formatting(page: Page, visit: Callable[[str], None], ask: Callable[[str], None]):
    visit("/c/new")
    ask(
        "\n\n".join([
            "Bilan",
            "| Colonne | Valeur |\n|---|---|\n| a | ligne 1<br>ligne 2 |",
            "```python\nprint(1)\n```",
            "[Documentation](https://example.org/doc)",
            "<details><summary>Plus</summary>Détail caché</details>",
            "H<sub>2</sub>O et 10<sup>3</sup>",
            "- [x] fait\n- [ ] à faire",
            "```mermaid\ngraph TD\n  A[Ligne 1<br/>ligne 2] --> B\n```",
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
        ("li input[type=checkbox][disabled]", 2),
        ("li input:checked", 1),
        (".mermaid svg .node br", 1),
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


@pytest.fixture
def report(page: Page) -> Iterator[int]:
    """Un rapport écrit par l'agent, porteur des charges et des graphiques, retiré ensuite."""
    content = f"# Rapport\n\n## Section\n\n{PAYLOADS}\n\n{CHARTS}"
    response = page.request.post("/api/reports", data={"title": "Rapport non fiable", "content": content})
    assert response.status == 201, response.text()
    report_id = response.json()["id"]
    yield report_id
    page.request.delete(f"/api/reports/{report_id}")


def test_a_report_page_runs_none_of_its_html(report: int, page: Page, visit: Callable[[str], None]):
    page.add_init_script(PROBE)
    requested = marker_requests(page)
    visit(f"/rapports/{report}")
    heading_ids = tuple(f"h{level}[id]" for level in range(1, 7))

    assert_stays_inert(page, "#reportBody", "Session expirée", requested, heading_ids, charts=len(DIAGRAMS))


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
    visit("/c/new")
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


def embed_json(body: str, script_id: str, value: object) -> str:
    """Remplace le JSON qu'embarque un élément <script> de la page, échappé comme le fait `tojson`."""
    return re.sub(
        rf'(<script id="{script_id}"[^>]*>).*?(</script>)',
        lambda match: match[1] + json.dumps(value).replace("<", "\\u003c") + match[2],
        body,
        flags=re.DOTALL,
    )


def with_knowledge_page(text: str, staged_files: list[str] | None = None) -> Callable[[Route], None]:
    """Remplace le texte d'une fiche de connaissance ; avec `staged_files`, sert sa discussion active et ces fichiers."""

    def replace(route: Route) -> None:
        response = route.fetch()
        body = embed_json(response.text(), "knowledgeRawContent", text)
        if staged_files is not None:
            body = (
                embed_json(body, "stagedFilesData", staged_files)
                .replace(
                    '<div class="markdown-body"',
                    '<button type="button" id="stagedFilesBtn">Fichiers</button><div class="markdown-body"',
                    1,
                )
                .replace("let currentConversationId = null;", "let currentConversationId = 'conversation';")
            )
        route.fulfill(response=response, body=body)

    return replace


@pytest.mark.parametrize("through_htmx", [False, True])
def test_a_knowledge_page_runs_none_of_its_html(page: Page, visit: Callable[[str], None], through_htmx: bool):
    page.add_init_script(PROBE)
    requested = marker_requests(page)
    page.route("**/knowledge/matomo/README.md", with_knowledge_page(f"**gras**\n\n{PAYLOADS}\n\n{CHARTS}"))
    if through_htmx:
        visit("/knowledge")
        page.locator('a[href="/knowledge/matomo/README.md"]').click()
    else:
        visit("/knowledge/matomo/README.md")
    expect(page.locator("#markdownContent strong")).to_have_text("gras")

    assert_stays_inert(page, "#markdownContent", "Session expirée", requested, charts=len(DIAGRAMS))


def test_without_the_sanitizer_a_knowledge_page_is_plain_text(page: Page, visit: Callable[[str], None]):
    page.add_init_script(PROBE)
    page.route("**/npm/dompurify@*/**", lambda route: route.abort())
    page.route("**/knowledge/matomo/README.md", with_knowledge_page("<img src=x onerror=probe(1)> **gras**"))
    visit("/knowledge/matomo/README.md")
    expect(page.locator("#markdownContent strong")).to_have_text("gras")

    assert_inert(page, "#markdownContent", "<img src=x onerror=probe(1)>", [])
    expect(page.locator("#markdownContent img")).to_have_count(0)


def test_a_staged_file_name_shows_as_text(page: Page, visit: Callable[[str], None]):
    page.add_init_script(PROBE)
    name = "<img src=x onerror=\"probe('staged')\">.md"
    page.route("**/knowledge/matomo/README.md", with_knowledge_page("Fiche", staged_files=[name]))
    visit("/knowledge/matomo/README.md")

    page.locator("#stagedFilesBtn").click()

    popover = page.locator(".popover-body")
    expect(popover.locator(".staged-file-link")).to_have_text(name)
    expect(popover.locator(".staged-file-link")).to_have_attribute("data-file", name)
    expect(popover.locator("#popoverCommitBtn, #popoverAbandonBtn")).to_have_count(2)
    page.wait_for_timeout(1000)
    expect(popover.locator("img")).to_have_count(0)
    assert probes(page) == []
