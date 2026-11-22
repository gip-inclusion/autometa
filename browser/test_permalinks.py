"""Preuves navigateur — lien vers une réponse, une section, un tableau, et mise en évidence à l'ouverture."""

import re
from collections.abc import Callable

import pytest
from playwright.sync_api import Locator, Page, expect

pytestmark = pytest.mark.browser

QUESTION = "Chiffres\n\n## Candidatures\n\n| Mois | Total |\n|---|---|\n| Janvier | 12 |\n\n## Méthode\n\nTexte."

# Why: le découpage du serveur voit un titre ou un tableau dans le bloc HTML, que le rendu laisse en texte ; il ne lit
# pas la citation, où le rendu en dessine un. Chaque cas donne la question, les titres affichés, puis ceux qui ont un lien.
DISAGREEMENTS = {
    "titres-différents": (
        "Désaccord\n\n## Contexte\n\n> ## Note importante\n> texte\n\n"
        "<details>\n## Détail des calculs\n</details>\n\n## Résultats",
        ["Contexte", "Note importante", "Résultats"],
        ["Contexte", "Résultats"],
    ),
    "même-titre": (
        "Désaccord\n\n## Contexte\n\n> ## Résultats\n> texte\n\n<details>\n## Résultats\ncalcul\n</details>\n\n## Méthode",
        ["Contexte", "Résultats", "Méthode"],
        ["Contexte", "Méthode"],
    ),
    "tableaux-de-même-forme": (
        "Désaccord\n\n## Chiffres\n\n<details>\n| a | b |\n|---|---|\n| 1 | 2 |\n</details>\n\n"
        "<table><thead><tr><th>x</th><th>y</th></tr></thead>"
        "<tbody><tr><td>3</td><td>4</td></tr><tr><td>5</td><td>6</td></tr></tbody></table>",
        ["Chiffres"],
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

NESTED = (
    "Plan\n\n## Candidatures\n\nTexte un.\n\n### Par mois\n\n| Mois | Total |\n|---|---|\n| Janvier | 12 |\n\n"
    "## Méthode\n\nTexte deux."
)

# Why: un lien survolé entoure ce qu'il partage ; on lit dans la page les enfants des réponses que couvre un contour,
# celui d'un élément ou celui que dessine le ::before d'un titre. Un titre s'y dit par son texte, une figure par sa sorte.
MARKED = """output => {
  const regions = [...output.querySelectorAll('*')].flatMap((element) => {
    const box = element.getBoundingClientRect();
    const before = getComputedStyle(element, '::before');
    if (getComputedStyle(element).outlineStyle !== 'none') return [[box.top, box.bottom]];
    return before.outlineStyle === 'none' ? [] : [[box.top, box.top + parseFloat(before.height)]];
  });
  return [...output.querySelectorAll('.event-assistant > :not(.permalink-btn)')]
    .filter((child) => {
      const box = child.getBoundingClientRect();
      return regions.some(([top, bottom]) => box.top >= top - 0.5 && box.bottom <= bottom + 0.5);
    })
    .map((child) => {
      const figure = child.matches('.permalink-figure');
      return figure ? child.firstElementChild.dataset.anchorKind : child.textContent.trim();
    });
}"""

BOXES = "output => [...output.querySelectorAll('*')].map((e) => JSON.stringify(e.getBoundingClientRect()))"

SECTION_LINK = "h2:has-text('Candidatures') > .permalink-btn"
TABLE_LINK = ".permalink-btn[data-url*='/table-1-']"

HOVERS = {
    "réponse": (
        NESTED,
        ":scope > .permalink-btn",
        ["Réponse factice : Plan", "Candidatures", "Texte un.", "Par mois", "table", "Méthode", "Texte deux."],
    ),
    "section": (NESTED, SECTION_LINK, ["Candidatures", "Texte un.", "Par mois", "table"]),
    "sous-section": (NESTED, "h3 > .permalink-btn", ["Par mois", "table"]),
    "dernière-section": (NESTED, "h2:has-text('Méthode') > .permalink-btn", ["Méthode", "Texte deux."]),
    "tableau": (NESTED, TABLE_LINK, ["table"]),
    "graphique": (CHART, ".permalink-btn[data-url*='/chart-1-']", ["chart"]),
}

# Why: Safari avant 17.4 n'a pas checkVisibility.
WITHOUT_CHECK_VISIBILITY = "delete Element.prototype.checkVisibility"


def answer_to(question: str, ask: Callable[[str], None], page: Page) -> Locator:
    ask(question)
    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    return page.locator(".event-final-answer").last


@pytest.fixture
def answer(conversation: str, ask: Callable[[str], None], page: Page):
    return answer_to(QUESTION, ask, page)


def test_a_finished_answer_offers_a_link_for_itself_each_section_and_each_table(answer, conversation: str):
    expect(answer.locator(".permalink-btn")).to_have_count(4)
    links = answer.locator(".permalink-btn").evaluate_all("buttons => buttons.map((b) => b.dataset.url)")

    shape = rf"/c/{conversation}/\d+(?:/(\w+-\d+)-[0-9a-f]{{6}})?"
    shapes = [re.fullmatch(shape, link) for link in links]
    assert all(shapes), links
    assert sorted(shape[1] for shape in shapes if shape[1]) == ["section-1", "section-2", "table-1"]


@pytest.mark.parametrize(("question", "headings", "linked"), DISAGREEMENTS.values(), ids=DISAGREEMENTS.keys())
def test_an_element_the_rendering_and_the_slicer_read_differently_gets_no_link_while_the_others_do(
    conversation: str, ask: Callable[[str], None], page: Page, question: str, headings: list[str], linked: list[str]
):
    answer = answer_to(question, ask, page)

    expect(answer.locator("h2")).to_have_text(headings)
    expect(answer.locator("[data-anchor]")).to_have_text(linked)
    expect(answer.locator(".permalink-btn")).to_have_count(1 + len(linked))
    expect(answer.locator(":is(blockquote, details, table) .permalink-btn, .permalink-figure")).to_have_count(0)
    expect(page.locator("#tocContent .toc-entry")).to_have_text(linked)


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


# Why: une empreinte dit le texte de l'élément ; à un autre rang elle le nomme encore, inconnue elle ne nomme que la réponse.
OPENED = {
    "tableau": (lambda link: link, "table.permalink-target"),
    "rang-décalé": (lambda link: link.replace("/table-1-", "/table-7-"), "table.permalink-target"),
    "empreinte-périmée": (lambda link: re.sub(r"[0-9a-f]{6}$", "000000", link), ".event-assistant.permalink-target"),
}


@pytest.mark.parametrize(("rewrite", "highlighted"), OPENED.values(), ids=OPENED.keys())
def test_opening_a_link_highlights_its_target_or_the_whole_answer_and_keeps_its_address(
    answer, visit: Callable[[str], None], page: Page, rewrite: Callable[[str], str], highlighted: str
):
    opened = rewrite(answer.locator(".permalink-btn[data-url*='/table-1-']").get_attribute("data-url"))

    visit(opened)

    expect(page.locator(highlighted)).to_have_count(1)
    expect(page.locator(".permalink-target")).to_have_count(1)
    expect(page).to_have_url(opened)
    expect(page.locator(".event-error")).to_have_count(0)


def test_a_link_opens_its_conversation_marked_in_the_sidebar_and_navigable(answer, conversation: str, page: Page):
    link = answer.locator(".permalink-btn[data-url*='/table-1-']").get_attribute("data-url")
    fresh = page.context.new_page()
    recent = fresh.locator(f"#sidebar-recents a[href='/c/{conversation}']")

    fresh.goto(link, wait_until="domcontentloaded")

    expect(fresh.locator("table.permalink-target")).to_have_count(1)
    expect(recent).to_have_class(re.compile(r"\bactive\b"))

    fresh.locator("#sidebar a[href='/c/new']").click()
    expect(fresh).to_have_url(re.compile(r"/c/new$"))
    recent.click()

    expect(fresh).to_have_url(re.compile(rf"/c/{conversation}$"))
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

    expect(page).to_have_url(re.compile(rf"/c/{conversation}/\d+/table-1-[0-9a-f]{{6}}$"))


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


@pytest.mark.parametrize(("question", "icon", "marked"), HOVERS.values(), ids=HOVERS.keys())
def test_hovering_a_link_outlines_what_it_shares_without_moving_anything(
    conversation: str, ask: Callable[[str], None], page: Page, question: str, icon: str, marked: list[str]
):
    link = answer_to(question, ask, page).locator(icon)
    output = page.locator("#chatOutput")
    link.scroll_into_view_if_needed()
    page.mouse.move(0, 0)
    boxes = output.evaluate(BOXES)

    link.hover()

    assert output.evaluate(MARKED) == marked
    assert output.evaluate(BOXES) == boxes
    page.mouse.move(0, 0)
    assert output.evaluate(MARKED) == []


def test_a_hover_outline_is_fainter_than_the_outline_of_an_opened_link(
    answer, visit: Callable[[str], None], page: Page
):
    visit(answer.locator(TABLE_LINK).get_attribute("data-url"))
    opened = page.locator(".event-final-answer").last
    target = opened.locator("table.permalink-target")
    expect(target).to_have_count(1)

    opened.locator(":scope > .permalink-btn").hover()

    expect(target).to_have_css("outline-width", "2px")
    style = "e => [parseFloat(getComputedStyle(e).outlineWidth), getComputedStyle(e).outlineColor]"
    (hovered_width, hovered_color), (target_width, target_color) = opened.evaluate(style), target.evaluate(style)
    assert 0 < hovered_width < target_width
    assert hovered_color != target_color


@pytest.mark.parametrize("icon", [SECTION_LINK, TABLE_LINK], ids=["section", "tableau"])
def test_an_outline_leaves_with_the_pointer_once_its_link_is_copied(answer, page: Page, icon: str):
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    output = page.locator("#chatOutput")
    link = answer.locator(icon)
    link.hover()
    assert output.evaluate(MARKED) != []

    link.click()
    page.mouse.move(0, 0)

    assert output.evaluate(MARKED) == []


def test_a_keyboard_focus_on_a_heading_link_outlines_its_section_until_it_moves(answer, page: Page):
    output = page.locator("#chatOutput")
    answer.locator(":scope > .permalink-btn").focus()

    page.keyboard.press("Tab")

    expect(answer.locator(SECTION_LINK)).to_be_focused()
    assert output.evaluate(MARKED) == ["Candidatures", "table"]
    page.keyboard.press("Tab")
    assert output.evaluate(MARKED) == ["table"]
    page.keyboard.press("Tab")
    assert output.evaluate(MARKED) == ["Méthode", "Texte."]


def test_a_tap_on_a_heading_link_outlines_nothing(answer, conversation: str, page: Page, base_url: str):
    touch = page.context.browser.new_page(
        base_url=base_url, viewport={"width": 375, "height": 667}, is_mobile=True, has_touch=True
    )
    touch.goto(f"/c/{conversation}", wait_until="domcontentloaded")
    link = touch.locator(".event-final-answer").last.locator(SECTION_LINK)

    link.tap()

    assert touch.locator("#chatOutput").evaluate(MARKED) == []
    touch.close()


@pytest.mark.parametrize(
    ("opened", "toc_click"),
    [("/c/{conversation}", True), ("/c/{conversation}/999999999/table-1-000000", False)],
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

    page.locator(f"#sidebar-recents a[href='/c/{other}']").click()
    expect(page).to_have_url(re.compile(rf"/c/{other}$"))
    page.go_back()

    expect(page.locator(".event-final-answer")).to_have_count(2)
    expect(page.locator(".permalink-btn[data-url*='/table-1-']")).to_have_count(1)


def test_a_touch_screen_shows_the_heading_links_only(answer, conversation: str, page: Page, base_url: str):
    touch = page.context.browser.new_page(
        base_url=base_url, viewport={"width": 375, "height": 667}, is_mobile=True, has_touch=True
    )
    touch.goto(f"/c/{conversation}", wait_until="domcontentloaded")
    touched = touch.locator(".event-final-answer").last
    expect(touched.locator(".permalink-btn")).to_have_count(4)

    assert touch.evaluate("matchMedia('(hover: none)').matches")
    expect(touched.locator("h2 .permalink-btn:visible")).to_have_count(2)
    expect(touched.locator(".permalink-figure > .permalink-btn")).to_have_css("display", "none")
    expect(touched.locator(":scope > .permalink-btn")).to_have_css("display", "none")
    touch.close()


def test_a_figure_is_wrapped_once_however_often_its_page_is_installed(answer, conversation: str, page: Page):
    other = page.request.post("/api/conversations").json()["id"]
    page.reload(wait_until="domcontentloaded")
    page.locator(f"#sidebar-recents a[href='/c/{other}']").click()
    page.wait_for_function("(id) => currentConversationId === id", arg=other)

    page.go_back()

    again = page.locator(".event-final-answer").last
    expect(again.locator(".permalink-btn")).to_have_count(4)
    expect(again.locator(".permalink-figure")).to_have_count(1)
    expect(again.locator(".permalink-figure > table")).to_have_count(1)


@pytest.mark.parametrize("address", ["/c/{conversation}", "/explorations/{conversation}"], ids=["adresse", "ancienne"])
def test_a_heading_link_from_before_permalinks_still_lands(
    conversation: str, ask: Callable[[str], None], page: Page, address: str
):
    answer_to(LONG, ask, page)
    fresh = page.context.new_page()

    fresh.goto(f"{address.format(conversation=conversation)}#methode", wait_until="domcontentloaded")

    expect(fresh.locator("h2#methode")).to_be_in_viewport()
    expect(fresh).to_have_url(re.compile(rf"/c/{conversation}#methode$"))


def test_a_conversation_opened_at_its_address_keeps_it_and_plays_a_turn(
    conversation: str, visit: Callable[[str], None], ask: Callable[[str], None], page: Page
):
    address = f"/c/{conversation}"

    visit(address)

    expect(page.locator(".event-final-answer")).to_have_count(1)
    expect(page).to_have_url(re.compile(rf"{address}$"))
    expect(page.locator(f"#sidebar-recents a[href='{address}']")).to_have_class(re.compile(r"\bactive\b"))

    ask("Deuxième question")

    expect(page.locator(".event-final-answer").last).to_contain_text("Deuxième question", timeout=15_000)
    expect(page.locator(".event-final-answer")).to_have_count(2)
    expect(page).to_have_url(re.compile(rf"{address}$"))

    page.locator("#sidebar a[href='/c/new']").click()
    expect(page).to_have_url(re.compile(r"/c/new$"))
    page.go_back()

    expect(page).to_have_url(re.compile(rf"{address}$"))
    expect(page.locator(".event-final-answer")).to_have_count(2)


def test_a_link_to_an_answer_not_displayed_opens_the_conversation_at_its_end(
    answer, ask: Callable[[str], None], page: Page
):
    link = answer.locator(".permalink-btn[data-url*='/table-1-']").get_attribute("data-url")
    answer_to(LONG, ask, page)
    fresh = page.context.new_page()
    # Why: la vue minimale masque ainsi les réponses intermédiaires, que l'agent factice ne sait pas produire ; sur le
    # document, pour que le style soit là quand la page s'installe.
    fresh.add_init_script(
        "document.addEventListener('DOMContentLoaded', () => document.head.insertAdjacentHTML("
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

    visit(f"/c/{opened}/{message}/table-1-000000")

    expect(page.locator(".event-error")).to_have_text("Ce lien ne correspond à aucune réponse de cette conversation.")
    expect(page).to_have_url(re.compile(rf"/c/{opened}$"))
    expect(page.locator(".permalink-target")).to_have_count(0)

    ask("Encore une question")

    expect(page.locator(".event-final-answer").last).to_contain_text("Réponse factice : Encore", timeout=15_000)
    expect(page.locator(".event-error")).to_have_count(1)


# Why: les actions de la barre latérale et la reprise du rendu sont des compléments ; le tour, lui, vient du flux.
FAILURES = {
    "actions-injoignables": lambda fresh, conv: fresh.route(f"**/api/conversations/{conv}", lambda r: r.abort()),
    "actions-illisibles": lambda fresh, conv: fresh.route(
        f"**/api/conversations/{conv}", lambda r: r.fulfill(status=200, body="<html>")
    ),
    "rendu-injoignable": lambda fresh, conv: fresh.route("**/blocks*", lambda r: r.abort()),
}


@pytest.mark.parametrize("fail", FAILURES.values(), ids=FAILURES.keys())
def test_a_running_conversation_resumes_when_what_completes_its_page_fails(
    conversation: str, ask: Callable[[str], None], page: Page, fail: Callable[[Page, str], None]
):
    ask("[slow:6] Longue réponse")
    expect(page.locator("#chatCancelBtn")).to_be_visible()
    fresh = page.context.new_page()
    fail(fresh, conversation)

    fresh.goto(f"/c/{conversation}", wait_until="domcontentloaded")

    expect(fresh.locator(".event-final-answer").last).to_contain_text("Réponse factice : [slow:6]", timeout=15_000)


@pytest.mark.parametrize("elsewhere", [False, True], ids=["nouvelle-conversation", "autre-conversation"])
def test_a_first_message_is_not_sent_once_the_page_has_left_its_conversation(
    conversation: str, page: Page, elsewhere: bool
):
    target = page.request.post("/api/conversations").json()["id"]
    destination = f"/c/{conversation}" if elsewhere else "/c/new"
    fresh = page.context.new_page()
    held = []

    def hold_the_first(route):
        if held:
            route.continue_()
        else:
            held.append(route)

    # Why: le premier message part une fois la page installée, ce qui attend le rendu des tours de la conversation.
    fresh.route(f"**/api/conversations/{target}/blocks*", hold_the_first)
    with fresh.expect_request(f"**/api/conversations/{target}/blocks*"):
        fresh.goto(f"/c/{target}?message=Bonjour", wait_until="domcontentloaded")
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
