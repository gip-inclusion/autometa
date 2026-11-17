"""Preuves navigateur — identifiants de message sur les blocs, reprise du flux sans rechargement."""

import re
from collections.abc import Callable

import pytest
from playwright.sync_api import Page, Route, expect

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
    page.locator(".event-user").first.evaluate("block => { block.dataset.probe = 'kept'; }")

    with page.expect_request(re.compile(rf"/stream\?after={growing.get_attribute('data-msg-id')}$")):
        page.evaluate(trigger)

    expect(page.locator(".event-final-answer")).to_have_count(2, timeout=15_000)
    assert growing.inner_text().count("Morceau 1.") == 1
    expect(page.locator(".event-user[data-probe=kept]")).to_have_count(1)
    expect(page.locator(".event-error")).to_have_count(0)

    streamed = page.locator(".event-block").all_inner_texts()
    page.reload(wait_until="domcontentloaded")
    expect(page.locator(".event-final-answer")).to_have_count(2)
    assert page.locator(".event-block").all_inner_texts() == streamed


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


def test_a_late_load_does_not_blank_the_conversation(conversation: str, page: Page):
    shown = page.locator(".event-block").count()
    held: list[Route] = []
    page.route(f"**/api/conversations/{conversation}", lambda route: route.continue_() if held else held.append(route))
    page.evaluate("id => { loadConversation(id); }", conversation)
    while not held:
        page.wait_for_timeout(20)

    page.evaluate("id => loadConversation(id)", conversation)
    with page.expect_response(f"**/api/conversations/{conversation}"):
        held[0].continue_()
    page.wait_for_timeout(300)

    expect(page.locator(".event-block")).to_have_count(shown)
