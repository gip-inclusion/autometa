"""Preuves navigateur — identifiants de message sur les blocs, reprise du flux sans rechargement."""

import re
from collections.abc import Callable

import pytest
from playwright.sync_api import Page, Route, expect

from web.database import store

pytestmark = pytest.mark.browser

RECONNECTS = {
    "connexion perdue": "eventSource.onerror()",
    "rotation du serveur": "eventSource.dispatchEvent(new MessageEvent('timeout', { data: '{}' }))",
}


def stored_ids(page: Page, conversation: str, kind: str) -> list[int]:
    messages = page.request.get(f"/api/conversations/{conversation}").json()["messages"]
    return [message["id"] for message in messages if message["type"] == kind]


def block_ids(page: Page, kind: str) -> list[int]:
    return page.locator(f".event-{kind}").evaluate_all(
        "blocks => blocks.flatMap((block) => block.dataset.msgId.split(' ').map(Number))"
    )


@pytest.mark.parametrize("reload", [False, True], ids=["flux", "rechargement"])
def test_blocks_carry_their_message_ids(conversation: str, ask: Callable[[str], None], page: Page, reload: bool):
    ask("Deuxième question")
    expect(page.locator(".event-final-answer")).to_have_count(2)
    if reload:
        page.reload(wait_until="domcontentloaded")
        expect(page.locator(".event-final-answer")).to_have_count(2)

    for kind in ("user", "assistant"):
        assert block_ids(page, kind) == stored_ids(page, conversation, kind)


@pytest.mark.parametrize("trigger", RECONNECTS.values(), ids=RECONNECTS.keys())
def test_reconnect_resumes_without_reloading(conversation: str, ask: Callable[[str], None], page: Page, trigger: str):
    ask("[slow:4] Réponse lente")
    growing = page.locator(".event-assistant", has_text="Morceau 1.")
    expect(growing).to_be_visible()
    page.locator(".event-user").evaluate_all("blocks => blocks.forEach((block) => { block.dataset.probe = 'kept'; })")

    # Why: le flux reprend après le dernier tour que la page tient entier ; le tour en cours revient avec lui.
    settled = stored_ids(page, conversation, "user")[-1] - 1
    with page.expect_request(re.compile(rf"/stream\?after={settled}$")):
        page.evaluate(trigger)

    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    assert growing.inner_text().count("Morceau 1.") == 1
    # Why: revenue telle qu'elle était avec la reprise du flux, la question du tour en cours reste en place elle aussi.
    expect(page.locator(".event-user[data-probe=kept]")).to_have_count(2)
    expect(page.locator(".event-error")).to_have_count(0)

    streamed = page.locator(".event-block").all_inner_texts()
    page.reload(wait_until="domcontentloaded")
    expect(page.locator(".event-final-answer")).to_have_count(2)
    assert page.locator(".event-block").all_inner_texts() == streamed


# Why: htmx installe la page suivante un moment après l'avoir échangée ; allongé, ce moment laisse au flux de la
# conversation quittée le temps d'apporter la suite de son tour.
SLOW_SETTLE = "document.addEventListener('DOMContentLoaded', () => { htmx.config.defaultSettleDelay = 2500; })"
# Why: sans la fermeture du flux au départ de la page, pour que seul le refus de ses événements soit éprouvé.
KEEP_THE_STREAM = "closeEventSource = () => {}"


@pytest.mark.parametrize("closed", [True, False], ids=["flux-fermé-au-départ", "flux-resté-ouvert"])
def test_the_stream_of_a_conversation_left_by_the_sidebar_writes_nothing_in_the_next_one(
    conversation: str, ask: Callable[[str], None], page: Page, closed: bool
):
    other = page.request.post("/api/conversations").json()["id"]
    page.add_init_script(SLOW_SETTLE)
    page.reload(wait_until="domcontentloaded")
    ask("[tools:1] [slow:5] Réponse lente")
    expect(page.locator(".event-assistant", has_text="Morceau 1.")).to_be_visible()
    if not closed:
        page.evaluate(KEEP_THE_STREAM)

    page.locator(f"#sidebar-recents a[href='/c/{other}']").click()
    expect(page.locator("#chatOutput[data-last-id='0']")).to_have_count(1)
    page.wait_for_timeout(2000)

    expect(page.locator("#chatOutput .event-block")).to_have_count(0)
    expect(page.locator("#chatOutput[data-last-id='0']")).to_have_count(1)
    expect(page.locator("#actionsContent .action-pill")).to_have_count(0)


@pytest.mark.parametrize("trigger", RECONNECTS.values(), ids=RECONNECTS.keys())
def test_a_pill_its_reader_opened_stays_open_when_the_stream_resumes(
    conversation: str, ask: Callable[[str], None], page: Page, trigger: str
):
    ask("[tools:2] [slow:4] Réponse lente")
    expect(page.locator(".event-assistant", has_text="Morceau 1.")).to_be_visible()
    page.locator(".sidebar-tab-btn[data-tab='actions']").click()
    page.locator(".actions-filter-btn[data-filter='detailed']").click()
    pills = page.locator("#actionsContent .action-pill")
    pills.first.locator(".action-pill-header").click()
    pills.evaluate_all("pills => pills.forEach((pill) => { pill.dataset.probe = 'kept'; })")

    with page.expect_request(re.compile(r"/stream\?after=\d+$")):
        page.evaluate(trigger)

    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    expect(page.locator("#actionsContent .action-pill[data-probe=kept]")).to_have_count(2)
    expect(pills.first).to_have_class(re.compile(r"\bexpanded\b"))
    expect(pills.first.locator(".action-kv-value")).to_be_visible()


def test_text_rewritten_in_place_grows_live_without_repeating(
    conversation: str, ask: Callable[[str], None], page: Page
):
    ask("[slow:3] Réponse lente")
    answer = page.locator(".event-assistant").last
    expect(answer).to_contain_text("Morceau 3.", timeout=15_000)
    assert answer.inner_text().count("Morceau 1.") == 1


def test_headings_of_a_growing_answer_reach_the_table_of_contents(
    conversation: str, ask: Callable[[str], None], page: Page
):
    for turns in (2, 3):
        ask("[slow:1] Plan\n\n## Section A")
        expect(page.locator(".event-final-answer")).to_have_count(turns, timeout=15_000)

    expect(page.locator("#tocContent .toc-entry-text")).to_have_text(["Section A", "Section A"])
    assert page.locator(".event-assistant h2").evaluate_all("headings => headings.map((h) => h.id)") == [
        "section-a",
        "section-a-2",
    ]


def test_an_installation_overtaken_by_another_neither_blanks_the_conversation_nor_doubles_its_actions(
    conversation: str, ask: Callable[[str], None], page: Page
):
    ask("[tools:2] Avec des outils")
    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    shown = page.locator(".event-block").count()
    held: list[Route] = []
    page.route(
        f"**/api/conversations/{conversation}/stream*",
        lambda route: route.continue_() if held else held.append(route),
    )
    page.evaluate("id => { installConversation(id); }", conversation)
    while not held:
        page.wait_for_timeout(20)

    assert page.evaluate("id => installConversation(id)", conversation) is True
    page.wait_for_timeout(300)

    expect(page.locator(".event-block")).to_have_count(shown)
    expect(page.locator("#actionsContent .action-pill")).to_have_count(2)
    expect(page.locator(".action-footnote")).to_have_count(2)


def test_a_page_opened_during_a_turn_shows_the_finished_turns_then_follows_the_running_one(
    conversation: str, ask: Callable[[str], None], page: Page
):
    ask("[tools:1] [slow:4] Réponse lente")
    expect(page.locator(".event-assistant", has_text="Morceau 1.")).to_be_visible()
    fresh = page.context.new_page()
    served = fresh.request.get(f"/c/{conversation}").text()
    assert "Réponse factice : Première question" in served
    assert "Morceau 1." not in served and "Réponse lente" not in served

    fresh.goto(f"/c/{conversation}", wait_until="domcontentloaded")

    expect(fresh.locator("#chatOutput > [data-partial]", has_text="Morceau")).to_have_count(1)
    expect(fresh.locator("#chatCancelBtn")).to_be_visible()
    expect(fresh.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    expect(fresh.locator("#chatOutput > [data-partial]")).to_have_count(0)
    expect(fresh.locator("#chatCancelBtn")).to_be_hidden()
    for kind in ("user", "assistant"):
        assert block_ids(fresh, kind) == stored_ids(fresh, conversation, kind)
    expect(fresh.locator("#actionsContent .action-pill")).to_have_count(1)
    assert fresh.locator(".event-block").all_inner_texts() == page.locator(".event-block").all_inner_texts()


def test_asking_again_sends_the_last_question_of_the_thread_even_on_a_page_that_did_not_send_it(
    conversation: str, page: Page
):
    store.add_message(conversation, "user", "Partie de la file")
    store.add_message(conversation, "assistant", "Réponse à la file")
    page.reload(wait_until="domcontentloaded")
    expect(page.locator(".event-final-answer")).to_have_count(2)

    page.evaluate("recover()")

    expect(page.locator(".event-final-answer").last).to_contain_text(
        "Réponse factice : Partie de la file", timeout=15_000
    )
    expect(page.locator("#chatOutput .event-user")).to_have_text([
        "Première question",
        "Partie de la file",
        "Partie de la file",
    ])
    expect(page.locator(".event-error")).to_have_count(0)
