"""Preuves navigateur — lien vers une réponse, une section, un tableau, et mise en évidence à l'ouverture."""

import re
from collections.abc import Callable

import pytest
from playwright.sync_api import Locator, Page, expect

pytestmark = pytest.mark.browser

QUESTION = "Chiffres\n\n## Candidatures\n\n| Mois | Total |\n|---|---|\n| Janvier | 12 |\n\n## Méthode\n\nTexte."

# Why: le serveur voit un titre dans le bloc HTML, la page un titre dans la citation — autant de titres de part et
# d'autre ; dans DISAGREEMENTS, ni les mêmes, ni d'autres mais de même texte, ni des tableaux de même forme.
DISAGREEMENTS = {
    "titres-différents": (
        "Désaccord\n\n## Contexte\n\n> ## Note importante\n> texte\n\n"
        "<details>\n## Détail des calculs\n</details>\n\n## Résultats",
        ["Contexte", "Note importante", "Résultats"],
    ),
    "même-titre": (
        "Désaccord\n\n## Contexte\n\n> ## Résultats\n> texte\n\n<details>\n## Résultats\ncalcul\n</details>\n\n## Méthode",
        ["Contexte", "Résultats", "Méthode"],
    ),
    "tableaux-de-même-forme": (
        "Désaccord\n\n## Chiffres\n\n<details>\n| a | b |\n|---|---|\n| 1 | 2 |\n</details>\n\n"
        "<table><thead><tr><th>x</th><th>y</th></tr></thead>"
        "<tbody><tr><td>3</td><td>4</td></tr><tr><td>5</td><td>6</td></tr></tbody></table>",
        ["Chiffres"],
    ),
}

# Why: le serveur ne lit pas les citations ; la page les écarte aussi, et le reste de la réponse s'apparie.
QUOTED = (
    "Citation\n\n## Contexte\n\n> ## Note\n>\n> | a | b |\n> |---|---|\n> | 1 | 2 |\n\n"
    "| c | d |\n|---|---|\n| 3 | 4 |\n\n## Résultats"
)

# Why: le titre du serveur garde l'échappement « \# » ; le sommaire montre la section telle que la page l'affiche.
CHART = 'Graphique\n\n## Statuts \\#1\n\n```mermaid\npie title Par statut\n    "Acceptées" : 3\n    "Refusées" : 1\n```'

LONG = "Longue\n\n## Méthode\n\n" + "Une ligne de texte.\n\n" * 60 + "Fin."

# Why: Safari avant 17.4 n'a pas checkVisibility.
WITHOUT_CHECK_VISIBILITY = "delete Element.prototype.checkVisibility"

# Why: un navigateur plus ancien refuse :has() et lève une exception pendant la pose des liens.
WITHOUT_HAS = (
    "const select = Element.prototype.querySelectorAll;"
    "Element.prototype.querySelectorAll = function (selector) {"
    "  if (selector.includes(':has(')) throw new DOMException('unsupported', 'SyntaxError');"
    "  return select.call(this, selector);"
    "}"
)

# Why: la première demande de liens répond après la seconde, avec des ancres périmées (aucune).
STALE_FIRST = """async () => {
  const fetchAnchors = window.fetch;
  let release;
  const held = new Promise((resolve) => { release = resolve; });
  let calls = 0;
  window.fetch = async (url, options) => {
    calls += 1;
    if (calls > 1) return fetchAnchors(url, options);
    await held;
    return new Response(JSON.stringify({ anchors: {}, target: null }));
  };
  const first = refreshPermalinks();
  await refreshPermalinks();
  release();
  await first;
  window.fetch = fetchAnchors;
}"""


def answer_to(question: str, ask: Callable[[str], None], page: Page) -> Locator:
    ask(question)
    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    return page.locator(".event-final-answer").last


@pytest.fixture
def answer(conversation: str, ask: Callable[[str], None], page: Page):
    return answer_to(QUESTION, ask, page)


def test_a_finished_answer_offers_a_link_for_itself_each_section_and_each_table(
    answer, conversation: str, base_url: str
):
    expect(answer.locator(".permalink-btn")).to_have_count(4)
    links = answer.locator(".permalink-btn").evaluate_all("buttons => buttons.map((b) => b.dataset.url)")

    shape = rf"{base_url}/explorations/{conversation}/\d+(?:/(\w+-\d+)-[0-9a-f]{{6}})?"
    shapes = [re.fullmatch(shape, link) for link in links]
    assert all(shapes), links
    assert sorted(shape[1] for shape in shapes if shape[1]) == ["section-1", "section-2", "table-1"]


@pytest.mark.parametrize(("question", "headings"), DISAGREEMENTS.values(), ids=DISAGREEMENTS.keys())
def test_an_answer_the_page_reads_otherwise_than_the_server_keeps_its_own_link_only(
    conversation: str, ask: Callable[[str], None], page: Page, question: str, headings: list[str]
):
    answer = answer_to(question, ask, page)

    expect(answer.locator(".permalink-btn")).to_have_count(1)
    expect(answer.locator("[data-anchor]")).to_have_count(0)
    expect(answer.locator("h2")).to_have_text(headings)
    expect(page.locator("#tocContent .toc-entry")).to_have_text(headings)
    expect(page.locator("#tocContent .toc-entry.toc-level-1")).to_have_count(len(headings))


def test_a_quoted_heading_or_table_gets_no_link_while_the_rest_of_the_answer_does(
    conversation: str, ask: Callable[[str], None], page: Page
):
    answer = answer_to(QUOTED, ask, page)

    expect(answer.locator(".permalink-btn")).to_have_count(4)
    expect(answer.locator("blockquote :is(.permalink-btn, [data-anchor])")).to_have_count(0)
    expect(answer.locator("blockquote :is(h2, table)")).to_have_count(2)
    expect(answer.locator(".permalink-figure th")).to_have_text(["c", "d"])
    expect(page.locator("#tocContent .toc-entry")).to_have_text(["Contexte", "Contexte", "Résultats"])


def test_a_chart_gets_its_link_and_its_entry_in_the_table_of_contents(
    conversation: str, ask: Callable[[str], None], page: Page
):
    answer = answer_to(CHART, ask, page)

    expect(answer.locator(".permalink-btn[data-url*='/chart-1-']")).to_have_count(1)
    expect(page.locator("#tocContent .toc-entry")).to_have_text(["Statuts #1", "Par statut"])
    expect(page.locator("#tocContent .toc-entry").nth(1).locator(".ri-bar-chart-2-line")).to_have_count(1)


@pytest.mark.parametrize("follower", ["- note", "> note", "---"], ids=["liste", "citation", "filet"])
def test_a_table_closed_by_the_next_block_keeps_its_link(
    conversation: str, ask: Callable[[str], None], page: Page, follower: str
):
    answer = answer_to(f"Tableau\n\n## Chiffres\n\n| a | b |\n|---|---|\n| 1 | 2 |\n{follower}\n\n## Fin", ask, page)

    expect(answer.locator(".permalink-btn[data-url*='/table-1-']")).to_have_count(1)


@pytest.mark.parametrize(
    ("stale", "highlighted"),
    [(False, "table.permalink-target"), (True, ".event-assistant.permalink-target")],
    ids=["tableau", "empreinte-périmée"],
)
def test_opening_a_link_highlights_its_target_or_the_whole_answer_and_keeps_its_address(
    answer, visit: Callable[[str], None], page: Page, stale: bool, highlighted: str
):
    link = answer.locator(".permalink-btn[data-url*='/table-1-']").get_attribute("data-url")
    opened = re.sub(r"[0-9a-f]{6}$", "000000", link) if stale else link

    visit(opened)

    expect(page.locator(highlighted)).to_have_count(1)
    expect(page.locator(".permalink-target")).to_have_count(1)
    expect(page).to_have_url(opened)
    expect(page.locator(".event-error")).to_have_count(0)


def test_a_link_opens_its_conversation_marked_in_the_sidebar_and_navigable(answer, conversation: str, page: Page):
    link = answer.locator(".permalink-btn[data-url*='/table-1-']").get_attribute("data-url")
    fresh = page.context.new_page()
    recent = fresh.locator(f"#sidebar-recents a[href='/explorations/{conversation}']")

    fresh.goto(link, wait_until="domcontentloaded")

    expect(fresh.locator("table.permalink-target")).to_have_count(1)
    expect(recent).to_have_class(re.compile(r"\bactive\b"))

    fresh.locator("#sidebar a[href='/explorations/new']").click()
    expect(fresh).to_have_url(re.compile(r"/explorations/new$"))
    recent.click()

    expect(fresh).to_have_url(re.compile(rf"/explorations/{conversation}$"))
    expect(fresh.locator(".event-final-answer")).to_have_count(2)
    expect(recent).to_have_class(re.compile(r"\bactive\b"))


def test_a_link_highlights_its_target_in_a_browser_without_check_visibility(answer, page: Page):
    link = answer.locator(".permalink-btn[data-url*='/table-1-']").get_attribute("data-url")
    fresh = page.context.new_page()
    fresh.add_init_script(WITHOUT_CHECK_VISIBILITY)

    fresh.goto(link, wait_until="domcontentloaded")

    expect(fresh.locator("table.permalink-target")).to_have_count(1)


def test_the_table_of_contents_outlines_sections_and_figures(answer, conversation: str, page: Page):
    entries = page.locator("#tocContent .toc-entry")

    expect(entries).to_have_text(["Candidatures", "Candidatures", "Méthode"])
    expect(entries.nth(1)).to_have_class(re.compile(r"\btoc-level-3\b"))
    expect(entries.nth(1).locator(".ri-table-line")).to_have_count(1)

    entries.nth(1).dispatch_event("click")

    expect(page).to_have_url(re.compile(rf"/explorations/{conversation}/\d+/table-1-[0-9a-f]{{6}}$"))


def test_a_heading_link_shows_at_rest_and_a_figure_link_only_under_the_pointer_over_its_corner(answer, page: Page):
    table = answer.locator("table")
    figure_link = answer.locator(".permalink-btn[data-url*='/table-1-']")
    expect(figure_link).to_have_count(1)

    page.mouse.move(0, 0)

    expect(answer.locator("h2 .permalink-btn").first).not_to_have_css("opacity", "0")
    expect(figure_link).to_have_css("opacity", "0")

    table.hover()

    expect(figure_link).not_to_have_css("opacity", "0")
    link_box, table_box = figure_link.bounding_box(), table.bounding_box()
    assert table_box["x"] <= link_box["x"] and link_box["x"] + link_box["width"] <= table_box["x"] + table_box["width"]
    assert table_box["y"] <= link_box["y"] < table_box["y"] + table_box["height"] / 2


@pytest.mark.parametrize(
    ("opened", "toc_click"),
    [("/explorations/{conversation}", True), ("/explorations/{conversation}/999999999/table-1-000000", False)],
    ids=["entrée-du-sommaire", "lien-vers-aucune-réponse"],
)
def test_going_back_to_a_conversation_whose_address_the_page_changed_shows_its_answers(
    answer, conversation: str, visit: Callable[[str], None], page: Page, opened: str, toc_click: bool
):
    other = page.request.post("/api/conversations").json()["id"]
    visit(opened.format(conversation=conversation))
    expect(page.locator(".event-final-answer")).to_have_count(2)
    if toc_click:
        page.locator("#tocContent .toc-entry").nth(1).dispatch_event("click")
    expect(page).not_to_have_url(re.compile(re.escape(opened.format(conversation=conversation)) + "$"))

    page.locator(f"#sidebar-recents a[href='/explorations/{other}']").click()
    expect(page).to_have_url(re.compile(rf"/explorations/{other}$"))
    page.go_back()

    expect(page.locator(".event-final-answer")).to_have_count(2)
    expect(page.locator(".permalink-btn[data-url*='/table-1-']")).to_have_count(1)


def test_a_touch_screen_shows_the_heading_links_only(answer, conversation: str, page: Page, base_url: str):
    touch = page.context.browser.new_page(
        base_url=base_url, viewport={"width": 375, "height": 667}, is_mobile=True, has_touch=True
    )
    touch.goto(f"/explorations/{conversation}", wait_until="domcontentloaded")
    touched = touch.locator(".event-final-answer").last
    expect(touched.locator(".permalink-btn")).to_have_count(4)

    assert touch.evaluate("matchMedia('(hover: none)').matches")
    expect(touched.locator("h2 .permalink-btn:visible")).to_have_count(2)
    expect(touched.locator(".permalink-figure > .permalink-btn")).to_have_css("display", "none")
    expect(touched.locator(":scope > .permalink-btn")).to_have_css("display", "none")
    touch.close()


def test_putting_the_links_again_wraps_each_figure_once(answer, page: Page):
    expect(answer.locator(".permalink-btn")).to_have_count(4)

    page.evaluate("refreshPermalinks()")
    page.evaluate("refreshPermalinks()")

    expect(answer.locator(".permalink-btn")).to_have_count(4)
    expect(answer.locator(".permalink-figure")).to_have_count(1)
    expect(answer.locator(".permalink-figure > table")).to_have_count(1)


def test_a_heading_link_from_before_permalinks_still_lands(conversation: str, ask: Callable[[str], None], page: Page):
    answer_to(LONG, ask, page)
    fresh = page.context.new_page()

    fresh.goto(f"/explorations/{conversation}#methode", wait_until="domcontentloaded")

    expect(fresh.locator("h2#methode")).to_be_in_viewport()


def test_a_conversation_opened_at_its_address_keeps_it_and_plays_a_turn(
    conversation: str, visit: Callable[[str], None], ask: Callable[[str], None], page: Page
):
    address = f"/explorations/{conversation}"

    visit(address)

    expect(page.locator(".event-final-answer")).to_have_count(1)
    expect(page).to_have_url(re.compile(rf"{address}$"))
    expect(page.locator(f"#sidebar-recents a[href='{address}']")).to_have_class(re.compile(r"\bactive\b"))

    ask("Deuxième question")

    expect(page.locator(".event-final-answer").last).to_contain_text("Deuxième question", timeout=15_000)
    expect(page.locator(".event-final-answer")).to_have_count(2)
    expect(page).to_have_url(re.compile(rf"{address}$"))

    page.locator("#sidebar a[href='/explorations/new']").click()
    expect(page).to_have_url(re.compile(r"/explorations/new$"))
    page.go_back()

    expect(page).to_have_url(re.compile(rf"{address}$"))
    expect(page.locator(".event-final-answer")).to_have_count(2)


def test_a_link_to_an_answer_not_displayed_opens_the_conversation_at_its_end(
    answer, ask: Callable[[str], None], page: Page
):
    link = answer.locator(".permalink-btn[data-url*='/table-1-']").get_attribute("data-url")
    answer_to(LONG, ask, page)
    fresh = page.context.new_page()
    # Why: la vue minimale masque ainsi les réponses intermédiaires, que l'agent factice ne sait pas produire.
    fresh.add_init_script(
        "addEventListener('DOMContentLoaded', () => document.head.insertAdjacentHTML("
        "'beforeend', '<style>.event-assistant:has(table) { display: none }</style>'))"
    )
    fresh.add_init_script(WITHOUT_CHECK_VISIBILITY)

    fresh.goto(link, wait_until="domcontentloaded")

    expect(fresh.locator(".event-final-answer").last.get_by_text("Fin.")).to_be_in_viewport()
    expect(fresh.locator(".permalink-target")).to_have_count(0)
    expect(fresh.locator(".event-error")).to_have_count(0)


@pytest.mark.parametrize(
    ("message_type", "elsewhere"),
    [("assistant", True), ("user", False), ("inconnu", False)],
    ids=["réponse-d-une-autre-conversation", "question", "message-inconnu"],
)
def test_a_link_naming_none_of_its_conversation_s_answers_opens_it_at_its_plain_address_and_says_so(
    conversation: str,
    visit: Callable[[str], None],
    ask: Callable[[str], None],
    page: Page,
    message_type: str,
    elsewhere: bool,
):
    messages = page.request.get(f"/api/conversations/{conversation}").json()["messages"]
    message = next((m["id"] for m in messages if m["type"] == message_type), 999_999_999)
    opened = page.request.post("/api/conversations").json()["id"] if elsewhere else conversation

    visit(f"/explorations/{opened}/{message}/table-1-000000")

    expect(page.locator(".event-error")).to_have_text("Ce lien ne correspond à aucune réponse de cette conversation.")
    expect(page).to_have_url(re.compile(rf"/explorations/{opened}$"))
    expect(page.locator(".permalink-target")).to_have_count(0)

    ask("Encore une question")

    expect(page.locator(".event-final-answer").last).to_contain_text("Réponse factice : Encore", timeout=15_000)
    expect(page.locator(".event-error")).to_have_count(1)


def test_the_permalink_request_carries_the_link_and_nothing_else(conversation: str, page: Page):
    fresh = page.context.new_page()

    with fresh.expect_request("**/anchors*") as request:
        fresh.goto(f"/explorations/{conversation}/1/table-1-000000?utm_source=slack", wait_until="domcontentloaded")

    assert request.value.url.endswith(f"/api/conversations/{conversation}/anchors?m=1&a=table-1-000000")


@pytest.mark.parametrize(
    "fail",
    [
        lambda fresh: fresh.route("**/anchors*", lambda route: route.abort()),
        lambda fresh: fresh.route("**/anchors*", lambda route: route.fulfill(status=200, body="<html>")),
        lambda fresh: fresh.add_init_script(WITHOUT_HAS),
    ],
    ids=["réseau", "réponse-illisible", "sélecteur-refusé"],
)
def test_a_running_conversation_resumes_when_its_permalinks_fail(
    conversation: str, ask: Callable[[str], None], page: Page, fail: Callable[[Page], None]
):
    ask("[slow:6] Longue réponse")
    expect(page.locator("#chatCancelBtn")).to_be_visible()
    fresh = page.context.new_page()
    fail(fresh)

    fresh.goto(f"/explorations/{conversation}", wait_until="domcontentloaded")

    expect(fresh.locator(".event-final-answer").last).to_contain_text("Réponse factice : [slow:6]", timeout=15_000)


def test_only_the_latest_request_for_links_applies(answer, page: Page):
    expect(answer.locator(".permalink-btn")).to_have_count(4)

    page.evaluate(STALE_FIRST)

    expect(answer.locator(".permalink-btn")).to_have_count(4)


@pytest.mark.parametrize("elsewhere", [False, True], ids=["nouvelle-conversation", "autre-conversation"])
def test_a_first_message_is_not_sent_once_the_page_has_left_its_conversation(
    conversation: str, page: Page, elsewhere: bool
):
    target = page.request.post("/api/conversations").json()["id"]
    destination = f"/explorations/{conversation}" if elsewhere else "/explorations/new"
    fresh = page.context.new_page()
    held = []

    def hold_the_first(route):
        if held:
            route.continue_()
        else:
            held.append(route)

    fresh.route("**/anchors*", hold_the_first)
    with fresh.expect_request(f"**/{target}/anchors*"):
        fresh.goto(f"/explorations/{target}?message=Bonjour", wait_until="domcontentloaded")
    fresh.locator(f"#sidebar a[href='{destination}']").click()
    # Why: htmx écrit l'adresse avant d'installer la page ; on attend qu'elle ait pris sa conversation.
    fresh.wait_for_function("(id) => currentConversationId === id", arg=conversation if elsewhere else None)

    held[0].continue_()
    fresh.wait_for_timeout(1500)

    expect(fresh).to_have_url(re.compile(rf"{destination}$"))
    expect(fresh.locator("#chatOutput .event-user", has_text="Bonjour")).to_have_count(0)
    for conv_id in (target, conversation):
        messages = page.request.get(f"/api/conversations/{conv_id}").json()["messages"]
        assert "Bonjour" not in [m["content"] for m in messages]


def test_an_answer_gets_its_links_as_soon_as_a_waiting_message_follows_it(
    conversation: str, ask: Callable[[str], None], page: Page
):
    ask("[slow:2] Chiffres\n\n## Candidatures")
    expect(page.locator("#chatCancelBtn")).to_be_visible()
    queued = page.request.post(
        f"/api/conversations/{conversation}/messages", data={"content": "[slow:8] Suite", "queue": True}
    )
    assert queued.json()["status"] == "queued"

    expect(page.locator("#chatOutput .event-user").last).to_have_text("[slow:8] Suite", timeout=15_000)

    expect(page.locator(".permalink-btn[data-url*='/section-1-']")).to_have_count(1, timeout=4_000)
