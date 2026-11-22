/**
 * Messages written during a turn: sent later, shown as waiting bubbles, given back to the composer.
 * The server holds the queue; the page only draws what it says.
 * Depends on: utils.js (appendToComposer, isAtBottom, scrollToBottom),
 *             render.js (formatUserContent, showError),
 *             stream.js (currentConversationId, setSending, startStream)
 */

/**
 * Queue a message on the running turn; it starts a turn instead if that one has just ended
 */
async function queueMessage(convId, message) {
  setSending(true);
  try {
    const response = await fetch(`/api/conversations/${convId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: message, queue: true }),
    });
    const data = await response.json();
    if (currentConversationId !== convId) return;

    // Why: the stream draws what follows — the bubble, or, if the turn had just ended, the end of its answer then the
    // question. This answer can be older than what the stream already drew.
    if (data.status === 'started') {
      startStream();
    } else if (data.status !== 'queued') {
      appendToComposer(message);
      showError(data.error || "Erreur lors de l'envoi");
    }
  } catch (error) {
    console.error('Failed to queue message:', error);
    if (currentConversationId === convId) {
      appendToComposer(message);
      showError('Erreur de connexion');
    }
  } finally {
    setSending(false);
  }
}

/**
 * Draw the waiting messages, in the order they were written
 */
function renderQueue(entries) {
  const queue = document.getElementById('chatQueue');
  if (!queue) return;
  const wasAtBottom = isAtBottom();
  queue.replaceChildren(
    ...entries.map((entry) => {
      const bubble = document.createElement('div');
      bubble.className = 'event-block event-user event-queued';
      bubble.dataset.queueId = entry.id;
      bubble.tabIndex = 0;
      bubble.role = 'button';
      bubble.title = 'Reprendre dans la barre de saisie';
      // Safe: formatUserContent escapes all user text via escapeHtml()
      bubble.innerHTML = `${formatUserContent(entry.content)}
        <button type="button" class="queued-remove" title="Retirer" aria-label="Retirer"><i class="ri-close-line"></i></button>`;
      return bubble;
    }),
  );
  // Why: an empty queue moves nothing; a conversation just opened at a link's target stays there.
  if (wasAtBottom && entries.length) scrollToBottom();
}

/**
 * Take a message out of the queue; pulled back, its text goes to the composer
 */
async function takeQueued(bubble, toComposer) {
  const convId = currentConversationId;
  // Why: hidden at once, so a double click does not ask for it twice; shown again if the server still holds it,
  // since no `queue` event would redraw an unchanged queue.
  bubble.hidden = true;
  try {
    const response = await fetch(`/api/conversations/${convId}/queue/${bubble.dataset.queueId}`, { method: 'DELETE' });
    const data = await response.json();
    if (currentConversationId !== convId) return;
    if (response.ok || data.code === 'already_sent') bubble.remove();
    else bubble.hidden = false;
    if (!response.ok) return showError(data.error || 'Message introuvable');
    if (toComposer) appendToComposer(data.content);
  } catch (error) {
    console.error('Failed to take a queued message:', error);
    if (currentConversationId !== convId) return;
    bubble.hidden = false;
    showError('Erreur de connexion');
  }
}

/**
 * Put messages the server handed back (Stop, failed turn) in the composer
 */
async function takeReturned(convId, entries) {
  if (!entries.length || currentConversationId !== convId) return;
  try {
    const response = await fetch(`/api/conversations/${convId}/queue/returned/ack`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: entries.map((entry) => entry.id) }),
    });
    // Why: the stream and the Stop answer hand the same messages back, and so do other tabs; the server gives
    // them to the first that asks.
    for (const entry of (await response.json()).returned ?? []) appendToComposer(entry.content);
  } catch (error) {
    console.error('Failed to take returned messages:', error);
  }
}
