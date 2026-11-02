"""Le chat continue de répondre pendant qu'on cherche des conversations similaires."""

from collections.abc import Callable

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser

CONVERSATION_ID = "11111111-1111-4111-8111-111111111111"
SIMILAR_URL = f"**/api/conversations/{CONVERSATION_ID}/similar"


@pytest.fixture
def chat(visit: Callable[[str], None], page: Page):
    page.add_init_script("""
        window.streamStarts = 0;
        window.EventSource = class {
            constructor() {
                window.testStream = this;
                window.streamStarts++;
                this.listeners = {};
            }
            addEventListener(type, callback) { this.listeners[type] = callback; }
            close() {}
            emit(type, data) { this.listeners[type]({ data: JSON.stringify(data) }); }
        };
    """)
    page.route(
        f"**/api/conversations/{CONVERSATION_ID}/messages",
        lambda route: route.fulfill(json={"after_id": 1}),
    )
    visit("/explorations/new")
    page.wait_for_function("typeof sendToAgent === 'function'")
    page.evaluate("id => { currentConversationId = id; }", CONVERSATION_ID)
    return page


@pytest.mark.parametrize("viewport", [{"width": 1280, "height": 900}, {"width": 390, "height": 844}])
def test_suggestions_do_not_delay_stream_and_only_search_first_message(chat: Page, viewport):
    chat.set_viewport_size(viewport)
    pending = []
    chat.route(SIMILAR_URL, lambda route: pending.append(route))
    chat.locator("#chatInput").fill("Les visites du portail")
    with chat.expect_request(SIMILAR_URL):
        chat.locator("#chatSendBtn").click()

    chat.evaluate("testStream.emit('assistant', { content: 'Réponse en cours' })")
    expect(chat.locator("#chatOutput .event-assistant")).to_contain_text("Réponse en cours")
    expect(chat.locator("#similarConversations")).to_be_hidden()

    pending[0].fulfill(
        json={
            "conversations": [
                {"id": "related", "title": "Visites <script>injection</script>"},
                {"id": "second", "title": "Parcours des utilisateurs"},
                {"id": "third", "title": "Visites par département"},
            ]
        }
    )
    suggestions = chat.locator("#similarConversations")
    expect(suggestions).to_be_visible()
    expect(suggestions.locator("h2")).to_be_in_viewport()
    expect(suggestions.locator("a")).to_have_count(3)
    expect(suggestions.locator("a").first).to_have_text("Visites <script>injection</script>")
    expect(suggestions.locator("a").first).to_have_attribute("href", "/explorations/related")
    expect(suggestions.locator("a").first).to_have_attribute("target", "_blank")
    expect(suggestions.locator("p")).to_have_count(0)
    expect(suggestions.locator("script")).to_have_count(0)

    chat.evaluate("testStream.emit('assistant', { content: ' — les données arrivent.' })")
    if viewport["width"] >= 992:
        main_box = chat.locator(".chat-main").bounding_box()
        assert suggestions.bounding_box()["x"] >= main_box["x"] + main_box["width"]

    chat.evaluate("setStreamingState(false)")
    chat.locator("#chatInput").fill("Et pour le mois dernier ?")
    chat.locator("#chatSendBtn").click()
    chat.wait_for_function("window.streamStarts === 2")
    assert len(pending) == 1


@pytest.mark.parametrize("result", ["empty", "error", "network"])
def test_suggestions_stay_hidden_without_interrupting_chat(chat: Page, result):
    if result == "network":
        chat.route(SIMILAR_URL, lambda route: route.abort())
    else:
        status = 500 if result == "error" else 200
        chat.route(SIMILAR_URL, lambda route: route.fulfill(status=status, json={"conversations": []}))

    chat.locator("#chatInput").fill("Une nouvelle question")
    with chat.expect_request(SIMILAR_URL):
        chat.locator("#chatSendBtn").click()

    chat.evaluate("testStream.emit('assistant', { content: 'La réponse continue' })")
    expect(chat.locator("#chatOutput .event-assistant")).to_contain_text("La réponse continue")
    expect(chat.locator("#similarConversations")).to_be_hidden()


def test_pending_suggestions_do_not_appear_after_navigation(chat: Page):
    pending = []
    chat.route(SIMILAR_URL, lambda route: pending.append(route))
    chat.locator("#chatInput").fill("Une nouvelle question")
    with chat.expect_request(SIMILAR_URL):
        chat.locator("#chatSendBtn").click()

    chat.evaluate("""() => {
        const container = document.getElementById('similarConversations');
        container.replaceWith(container.cloneNode(false));
        currentConversationId = '22222222-2222-4222-8222-222222222222';
    }""")
    pending[0].fulfill(json={"conversations": [{"id": "related", "title": "Ancien sujet"}]})
    expect(chat.locator("#similarConversations")).to_be_hidden()
    expect(chat.locator("#similarConversations a")).to_have_count(0)
