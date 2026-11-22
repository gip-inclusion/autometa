"""Preuves navigateur — la page d'une conversation arrive dessinée par le serveur, sans attendre ses messages."""

import json
import re
from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

from web.database import store

pytestmark = pytest.mark.browser

FIGURES = "Chiffres\n\n## Candidatures\n\n| Mois | Total |\n|---|---|\n| Janvier | 12 |\n\n## Méthode\n\nTexte."
RICH = "[tools:1] Bilan\n\n## Plan\n\n- [x] fait\n- [ ] à faire\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n```options\nOui\nNon\n```"
BLOCKS = "blocks => blocks.map((block) => block.outerHTML)"
LONG = "Longue\n\n" + "Une ligne de texte.\n\n" * 60 + "Fin."
CHART = 'Graphique\n\n```mermaid\npie title Par statut\n    "Acceptées" : 3\n    "Refusées" : 1\n```'
# Why: chaque graphique que la page dessine entre dans le document comme un élément .mermaid.
COUNT_CHARTS = """document.addEventListener('DOMContentLoaded', () => {
  window.chartsDrawn = 0;
  new MutationObserver((records) => {
    for (const record of records) {
      for (const node of record.addedNodes) if (node.nodeType === 1 && node.matches('.mermaid')) window.chartsDrawn += 1;
    }
  }).observe(document.body, { childList: true, subtree: true });
})"""
# Why: à la première image d'une zone de conversation qui a ses blocs, on note où elle en est : distance à sa fin, et
# place du tableau du lien dans la zone visible (null s'il n'y est pas). La lecture se fait depuis un ResizeObserver
# créé à ce moment : il passe après la mise en page et après ceux de la page, juste avant que l'image soit peinte.
FIRST_FRAMES = """(() => {
  window.firstFrames = [];
  let seen = null;
  const look = () => {
    const output = document.getElementById('chatOutput');
    const main = document.querySelector('#chatWithSidebar .chat-main');
    if (main && output !== seen && output?.querySelector('.event-block')) {
      seen = output;
      new ResizeObserver((_, once) => {
        once.disconnect();
        const view = main.getBoundingClientRect();
        const table = output.querySelector('table[data-anchor]')?.getBoundingClientRect();
        window.firstFrames.push({
          fromEnd: Math.round(main.scrollHeight - main.scrollTop - main.clientHeight),
          table: table && table.top >= view.top - 1 && table.top < view.bottom ? Math.round(table.top - view.top) : null,
        });
      }).observe(output);
    }
    requestAnimationFrame(look);
  };
  requestAnimationFrame(look);
})()"""
MARK_TOC = "entries => entries.forEach((entry) => { entry.dataset.left = ''; })"


def hold_the_api(page: Page) -> None:
    """Laisse sans réponse ce que la page demande sur ses conversations : messages et rendu des tours."""
    page.route(re.compile(r"/api/conversations/[^/]+(/blocks.*)?$"), lambda route: None)


@pytest.fixture
def figures(conversation: str, ask: Callable[[str], None], page: Page) -> str:
    """Une conversation dont le second tour porte deux sections et un tableau."""
    ask(FIGURES)
    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    return conversation


def test_the_page_of_a_conversation_is_served_with_its_finished_turns_drawn(figures: str, page: Page):
    served = page.request.get(f"/c/{figures}").text()

    for drawn in (
        'class="event-block event-user"',
        "Réponse factice : Première question",
        "event-final-answer",
        "<h2 data-anchor=",
        '<div class="permalink-figure"><table data-anchor=',
        f'data-url="/c/{figures}/',
    ):
        assert drawn in served
    assert "loadingConversation" not in served


def test_a_conversation_shows_its_answers_and_its_link_s_target_before_any_of_its_messages_is_fetched(
    figures: str, page: Page
):
    link = page.locator(".permalink-btn[data-url*='/table-1-']").get_attribute("data-url")
    fresh = page.context.new_page()
    hold_the_api(fresh)

    fresh.goto(link, wait_until="domcontentloaded")

    expect(fresh.locator(".event-final-answer")).to_have_count(2)
    expect(fresh.locator("table.permalink-target")).to_be_in_viewport()
    expect(fresh.locator("#tocContent .toc-entry")).to_have_text(["Candidatures", "Candidatures", "Méthode"])
    expect(fresh).to_have_url(link)


def test_the_sidebar_back_and_forward_show_a_conversation_installed_without_waiting_for_its_messages(
    figures: str, visit: Callable[[str], None], page: Page
):
    other = page.request.post("/api/conversations").json()["id"]
    hold_the_api(page)
    visit(f"/c/{other}")
    page.evaluate("window.sameDocument = true")
    answers = page.locator(".event-final-answer")
    # Why: le sommaire est fait par l'installation ; une entrée marquée viendrait de la copie gardée par htmx.
    toc = page.locator("#tocContent .toc-entry")

    page.locator(f"#sidebar-recents a[href='/c/{figures}']").click()

    expect(answers).to_have_count(2)
    expect(answers.last.locator(".permalink-figure > table")).to_be_visible()
    expect(page.locator("#loadingConversation, #chatOutput .spinner")).to_have_count(0)
    expect(toc).to_have_count(3)
    toc.evaluate_all(MARK_TOC)

    page.go_back()
    expect(page).to_have_url(re.compile(rf"/c/{other}$"))
    expect(answers).to_have_count(0)
    page.go_forward()

    expect(answers).to_have_count(2)
    expect(toc).to_have_count(3)
    expect(page.locator("#tocContent .toc-entry[data-left]")).to_have_count(0)
    toc.evaluate_all(MARK_TOC)
    page.locator(f"#sidebar-recents a[href='/c/{other}']").click()
    expect(answers).to_have_count(0)
    page.go_back()

    expect(answers).to_have_count(2)
    expect(toc).to_have_count(3)
    expect(page.locator("#tocContent .toc-entry[data-left]")).to_have_count(0)
    expect(page.locator("#loadingConversation, #chatOutput .spinner")).to_have_count(0)
    assert page.evaluate("window.sameDocument") is True


def test_the_end_of_a_turn_leaves_the_blocks_a_reload_gives(conversation: str, ask: Callable[[str], None], page: Page):
    blocks = page.locator("#chatOutput > *")
    ask(RICH)
    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    expect(page.locator("#chatOutput > [data-live]")).to_have_count(0)
    expect(page.locator(".action-footnote")).to_have_count(1)
    expect(page.locator(".options-buttons button")).to_have_count(2)
    handed_over = blocks.evaluate_all(BLOCKS)

    page.reload(wait_until="domcontentloaded")

    expect(page.locator(".action-footnote")).to_have_count(1)
    assert blocks.evaluate_all(BLOCKS) == handed_over
    page.locator(".options-buttons button", has_text="Non").click()
    expect(page.locator("#chatInput")).to_have_value("Non")


def test_a_conversation_whose_rendered_turns_never_come_does_not_hold_the_next_one(
    conversation: str, visit: Callable[[str], None], ask: Callable[[str], None], page: Page
):
    other = page.request.post("/api/conversations").json()["id"]
    page.route(f"**/api/conversations/{conversation}/blocks*", lambda route: None)
    visit(f"/c/{conversation}")
    expect(page.locator(".event-final-answer")).to_have_count(1)

    page.locator(f"#sidebar-recents a[href='/c/{other}']").click()
    page.wait_for_function("(id) => currentConversationId === id", arg=other)
    ask("[tools:1] Dans l'autre")

    expect(page.locator(".event-final-answer")).to_contain_text(
        "Réponse factice : [tools:1] Dans l'autre", timeout=15_000
    )
    expect(page.locator("#chatOutput > [data-live]")).to_have_count(0)
    expect(page.locator("#actionsContent .action-pill")).to_have_count(1)
    page.request.post(f"/api/conversations/{other}/cancel")


def test_an_installation_that_fails_leaves_the_page_able_to_send(
    conversation: str, ask: Callable[[str], None], page: Page
):
    broken = """(id) => {
      const build = rebuildToc;
      rebuildToc = () => { rebuildToc = build; throw new Error('sommaire'); };
      return installConversation(id);
    }"""

    assert page.evaluate(broken, conversation) is False
    ask("Après l'échec")

    expect(page.locator(".event-final-answer").last).to_contain_text("Réponse factice : Après l'échec", timeout=15_000)
    expect(page.locator(".event-error")).to_have_count(0)


# Why: skip quand la cible ne sert pas la page à un administrateur : la relance est un bouton d'administrateur.
def test_back_onto_a_relaunched_turn_shows_its_question_once(fake_agent, visit: Callable[[str], None], page: Page):
    shared = store.create_conversation(user_id="quelqu.un@example.com").id
    for kind, content in [("user", "Première question"), ("assistant", "Réponse"), ("user", "[slow:4] relance")]:
        store.add_message(shared, kind, content)
    visit(f"/c/{shared}")
    if not page.locator("#relaunchBtn").count():
        store.delete_conversation(shared)
        pytest.skip("la cible n'est pas servie à un administrateur")
    page.locator("#relaunchBtn").click()
    expect(page.locator(".event-assistant", has_text="Morceau 1.")).to_be_visible(timeout=10_000)
    page.locator("#nav-primary a[href='/conversations?show=convos']").click()
    page.wait_for_url("**/conversations?show=convos")

    page.go_back()

    expect(page.locator(".event-final-answer").last).to_contain_text("Réponse factice : [slow:4]", timeout=20_000)
    expect(page.locator("#chatOutput > [data-live]")).to_have_count(0)
    expect(page.locator("#chatOutput .event-user")).to_have_text(["Première question", "[slow:4] relance"])
    store.delete_conversation(shared)


def test_an_answer_that_grew_after_its_turn_takes_the_place_of_the_one_shown(conversation: str, page: Page):
    blocks = page.locator("#chatOutput > *")
    expect(page.locator("#chatOutput > [data-live]")).to_have_count(0)
    store.add_message(conversation, "assistant", "\n\n*Interrompu.*")

    page.evaluate("syncOutput()")

    expect(page.locator(".event-final-answer em")).to_have_text("Interrompu.")
    expect(page.locator(".event-assistant")).to_have_count(1)
    synced = blocks.evaluate_all(BLOCKS)
    page.reload(wait_until="domcontentloaded")
    expect(page.locator(".event-final-answer em")).to_have_text("Interrompu.")
    assert blocks.evaluate_all(BLOCKS) == synced


def test_the_actions_of_a_turn_rendered_before_the_stream_brought_it_are_listed(
    conversation: str, ask: Callable[[str], None], page: Page
):
    page.route("**/stream*", lambda route: None)
    ask("[tools:2] Avec des outils")
    for _ in range(250):
        stored = page.request.get(f"/api/conversations/{conversation}").json()
        if not stored["is_running"] and "Avec des outils" in stored["messages"][-1]["content"]:
            break
        page.wait_for_timeout(20)

    page.evaluate("syncOutput()")

    expect(page.locator(".event-final-answer")).to_have_count(2)
    expect(page.locator("#actionsContent .action-pill")).to_have_count(2)
    expect(page.locator(".event-final-answer").last.locator(".action-footnote")).to_have_count(2)
    expect(page.locator("#chatOutput:not([data-running])")).to_have_count(1)


def test_a_chart_is_drawn_once_when_its_turn_ends(conversation: str, ask: Callable[[str], None], page: Page):
    page.add_init_script(COUNT_CHARTS)
    page.reload(wait_until="domcontentloaded")

    ask(CHART)

    expect(page.locator("#chatOutput > [data-live]")).to_have_count(0, timeout=15_000)
    expect(page.locator(".event-final-answer .permalink-figure > .mermaid svg")).to_have_count(1)
    assert page.evaluate("window.chartsDrawn") == 1


@pytest.mark.parametrize("named", ["tableau", "réponse"], ids=["élément-déjà-rendu", "réponse-finie-depuis"])
def test_a_link_opened_on_a_page_rendered_before_the_last_turn_lands_on_its_target(
    figures: str, page: Page, named: str
):
    table = page.locator(".permalink-btn[data-url*='/table-1-']").get_attribute("data-url")
    rendered_before = page.request.get(f"/c/{figures}").text()
    store.add_message(figures, "user", "Encore")
    answer = store.add_message(figures, "assistant", LONG)
    opened = table if named == "tableau" else f"/c/{figures}/{answer.id}"
    fresh = page.context.new_page()
    fresh.route(f"**{opened}", lambda route: route.fulfill(body=rendered_before, content_type="text/html"))

    # Why: la file, vide, est dessinée à la réception des messages ; elle ne doit pas ramener la page à sa fin.
    with fresh.expect_response(f"**/api/conversations/{figures}/actions"):
        fresh.goto(opened, wait_until="domcontentloaded")

    expect(fresh.locator(".event-final-answer")).to_have_count(3)
    expect(fresh.locator(".permalink-target")).to_have_count(1)
    expect(
        fresh.locator("table.permalink-target" if named == "tableau" else ".event-assistant.permalink-target")
    ).to_be_in_viewport()
    expect(fresh.locator(".event-error")).to_have_count(0)
    expect(fresh).to_have_url(opened)


def test_waiting_messages_bring_the_page_to_its_end_and_an_empty_queue_leaves_it(
    conversation: str, ask: Callable[[str], None], page: Page
):
    ask(LONG)
    expect(page.locator("#chatOutput > [data-live]")).to_have_count(0, timeout=15_000)
    first, end = page.locator(".event-user").first, page.locator(".event-final-answer").last.get_by_text("Fin.")
    first.scroll_into_view_if_needed()

    page.evaluate("renderQueue([])")
    expect(first).to_be_in_viewport()
    expect(end).not_to_be_in_viewport()
    page.evaluate("renderQueue([{ id: 'attente', content: 'En attente' }])")

    expect(page.locator("#chatQueue .event-queued")).to_have_text("En attente")
    expect(page.locator("#chatQueue .event-queued")).to_be_in_viewport()


def frames_once(page: Page, count: int) -> list[dict]:
    """Les premières images notées, une fois que la page en a noté `count` : la dernière l'est à l'image suivante."""
    page.wait_for_function("(count) => window.firstFrames.length >= count", arg=count)
    return page.evaluate("window.firstFrames")


@pytest.fixture
def long_after_figures(figures: str, ask: Callable[[str], None], page: Page) -> str:
    """La conversation aux figures, suivie d'un tour assez long pour que son tableau soit loin de sa fin."""
    ask(LONG)
    expect(page.locator(".event-final-answer")).to_have_count(3, timeout=15_000)
    return figures


def test_the_first_image_of_a_conversation_shows_its_end_however_it_is_opened(
    long_after_figures: str, visit: Callable[[str], None], page: Page
):
    other = page.request.post("/api/conversations").json()["id"]
    page.add_init_script(FIRST_FRAMES)
    answers = page.locator(".event-final-answer")

    visit(f"/c/{long_after_figures}")
    expect(answers).to_have_count(3)
    loaded = frames_once(page, 1)
    page.locator(f"#sidebar-recents a[href='/c/{other}']").click()
    expect(answers).to_have_count(0)
    page.locator(f"#sidebar-recents a[href='/c/{long_after_figures}']").click()
    expect(answers).to_have_count(3)
    page.locator(f"#sidebar-recents a[href='/c/{other}']").click()
    expect(answers).to_have_count(0)
    page.go_back()
    expect(answers).to_have_count(3)

    frames = frames_once(page, 3)
    assert [frame["fromEnd"] for frame in loaded] == [0]
    assert [frame["fromEnd"] for frame in frames] == [0, 0, 0]
    assert [frame["table"] for frame in frames] == [None, None, None]
    expect(answers.last.get_by_text("Fin.")).to_be_in_viewport()


def test_the_first_image_of_a_conversation_opened_at_a_link_shows_its_target(long_after_figures: str, page: Page):
    link = page.locator(".permalink-btn[data-url*='/table-1-']").get_attribute("data-url")
    fresh = page.context.new_page()
    fresh.add_init_script(FIRST_FRAMES)

    fresh.goto(link, wait_until="domcontentloaded")

    expect(fresh.locator("table.permalink-target")).to_be_in_viewport()
    (frame,) = frames_once(fresh, 1)
    assert frame["table"] is not None and frame["fromEnd"] > 0


def test_a_tool_call_the_stream_brought_without_its_result_is_listed_once_with_it(
    conversation: str, ask: Callable[[str], None], page: Page
):
    page.route("**/stream*", lambda route: None)
    ask("[tools:2] Avec des outils")
    for _ in range(250):
        stored = page.request.get(f"/api/conversations/{conversation}").json()
        if not stored["is_running"] and "Avec des outils" in stored["messages"][-1]["content"]:
            break
        page.wait_for_timeout(20)
    first_call = next(m["id"] for m in stored["messages"] if m["type"] == "tool_use")
    page.evaluate(
        "id => appendEvent('tool_use', { id, content: { tool: 'Bash', input: { command: 'echo 0' } } })", first_call
    )

    page.evaluate("syncOutput()")

    commands = page.locator("#actionsContent .action-pill .action-kv-value")
    expect(commands).to_have_text(["echo 0", "echo 1"])
    assert page.evaluate("pendingToolUses.length") == 0


def test_actions_that_could_not_be_read_are_built_the_next_time_turns_are_brought(
    conversation: str, ask: Callable[[str], None], page: Page
):
    ask("[tools:2] Avec des outils")
    expect(page.locator("#actionsContent .action-pill")).to_have_count(2, timeout=15_000)
    failed = []
    page.route(
        f"**/api/conversations/{conversation}/actions",
        lambda route: route.continue_() if failed else failed.append(route.abort()),
    )
    page.reload(wait_until="domcontentloaded")
    expect(page.locator(".event-final-answer")).to_have_count(2)
    page.wait_for_function("catchingUpFor === null && unreplayed.length === 1")
    expect(page.locator("#actionsContent .action-pill")).to_have_count(0)

    page.evaluate("syncOutput()")

    expect(page.locator("#actionsContent .action-pill")).to_have_count(2)
    expect(page.locator(".action-footnote")).to_have_count(2)


def test_conversations_the_page_has_left_are_let_go(figures: str, visit: Callable[[str], None], page: Page):
    other = page.request.post("/api/conversations").json()["id"]
    visit(f"/c/{figures}")
    page.evaluate(
        """() => {
          window.left = [];
          document.body.addEventListener('htmx:beforeSwap', (e) => {
            if (e.detail.target.id === 'main') window.left.push(new WeakRef(document.querySelector('.chat-main')));
          });
        }"""
    )
    for conversation in [other, figures, other, figures, other]:
        page.locator(f"#sidebar-recents a[href='/c/{conversation}']").click()
        page.wait_for_function("(id) => currentConversationId === id && !!conversationHold", arg=conversation)
    page.go_back()
    expect(page.locator(".event-final-answer")).to_have_count(2)

    # Why: seul le ramasse-miettes dit si une zone retirée de la page est encore tenue par un écouteur ou un observateur.
    session = page.context.new_cdp_session(page)
    for _ in range(2):
        session.send("HeapProfiler.collectGarbage")
    assert page.evaluate("[window.left.length, window.left.filter((ref) => ref.deref()).length]") == [5, 0]


# Why: ce que le navigateur compte lui-même comme déplacement d'éléments visibles, hors ceux qui suivent un geste.
SHIFTS = """() => {
  window.shifts = [];
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) if (!entry.hadRecentInput) window.shifts.push(entry.value);
  }).observe({ type: 'layout-shift' });
}"""


def test_nothing_moves_when_the_references_of_a_conversation_are_built(
    conversation: str, ask: Callable[[str], None], page: Page
):
    for turn, question in enumerate(["[tools:3] Un", "[tools:40] Deux", f"[tools:2] {LONG}"], 2):
        ask(question)
        expect(page.locator(".event-final-answer")).to_have_count(turn, timeout=15_000)
    references = page.locator("#chatOutput .action-footnote:not(.action-footnote-kept)")
    other = page.request.post("/api/conversations").json()["id"]
    held = []
    page.route(
        f"**/api/conversations/{conversation}/actions", lambda route: route.continue_() if held else held.append(route)
    )
    page.reload(wait_until="domcontentloaded")
    expect(page.locator("#chatOutput .action-footnote-kept")).to_have_count(45)
    expect(references).to_have_count(0)
    page.evaluate(SHIFTS)

    held[0].continue_()

    expect(references).to_have_count(45)
    expect(page.locator("#chatOutput .action-footnote-kept")).to_have_count(0)
    page.wait_for_timeout(300)
    assert page.evaluate("window.shifts") == []
    page.locator(f"#sidebar-recents a[href='/c/{other}']").click()
    page.wait_for_function("(id) => currentConversationId === id", arg=other)
    page.evaluate("window.shifts.length = 0")
    page.go_back()

    expect(references).to_have_count(45)
    page.wait_for_timeout(300)
    assert page.evaluate("window.shifts") == []


SIGNAL = '[AUTOMETA:API:{"source": "matomo", "method": "VisitsSummary.get"}]\n'


def test_opening_a_conversation_fetches_its_tool_calls_without_their_outputs(
    conversation: str, ask: Callable[[str], None], page: Page
):
    ask("[tools:3] Avec des outils")
    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    other = page.request.post("/api/conversations").json()["id"]
    pills = page.locator("#actionsContent .action-pill")

    def open_through_the_sidebar(target: str, shown: int) -> None:
        page.locator(f"#sidebar-recents a[href='/c/{target}']").click()
        # Why: htmx installe la page un instant après l'avoir échangée ; un Retour avant cela l'installerait deux fois.
        page.wait_for_function("(id) => currentConversationId === id && catchingUpFor === null", arg=target)
        expect(pills).to_have_count(shown)

    page.reload(wait_until="domcontentloaded")
    expect(pills).to_have_count(3)
    page.wait_for_function("catchingUpFor === null")
    asked = []
    page.on("request", lambda request: asked.append(request.url.split("/api/conversations/")[-1]))

    page.reload(wait_until="domcontentloaded")
    expect(pills).to_have_count(3)
    open_through_the_sidebar(other, 0)
    open_through_the_sidebar(conversation, 3)
    open_through_the_sidebar(other, 0)
    page.go_back()

    expect(pills).to_have_count(3)
    expect(page.locator(".action-footnote:not(.action-footnote-kept)")).to_have_count(3)
    assert asked.count(f"{conversation}/actions") == 3
    assert [url for url in asked if url == conversation or "/messages/" in url] == []


def test_a_value_cut_short_in_a_pill_is_fetched_whole_when_its_reader_asks(conversation: str, page: Page):
    command, output = "echo " + "é" * 600, "ligne\n" * 200
    ids = [
        store.add_message(conversation, kind, json.dumps(content)).id
        for kind, content in [
            ("tool_use", {"tool": "Bash", "category": "API: Matomo", "input": {"command": command}}),
            (
                "tool_result",
                {"output": {"tool": "Bash", "output": SIGNAL + output}, "api_calls": [{"source": "matomo"}]},
            ),
        ]
    ]
    page.reload(wait_until="domcontentloaded")
    asked = []
    page.on(
        "request",
        lambda request: asked.append(request.url.split("/messages/")[-1]) if "/messages/" in request.url else None,
    )
    page.locator(".sidebar-tab-btn[data-tab='actions']").click()
    page.locator(".actions-filter-btn[data-filter='detailed']").click()
    pill = page.locator("#actionsContent .action-pill")
    pill.locator(".action-pill-header").click()
    values = pill.locator(".action-kv")
    modal = page.locator("#actionDetailModalBody")

    expect(values.locator(".action-kv-value")).to_have_text([command[:500] + "...", output.strip()[:500] + "..."])
    assert asked == []
    values.nth(0).locator(".action-expand-btn").click()

    expect(modal).to_have_text(command)
    page.locator("#actionDetailModal .btn-close").click()
    expect(page.locator("#actionDetailModal")).to_be_hidden()
    values.nth(1).locator(".action-expand-btn").click()

    expect(modal.locator("pre")).to_have_text(output.strip())
    assert asked == [str(message_id) for message_id in ids]
