/**
 * Messages written during a turn: sent later, shown as waiting bubbles, given back to the composer.
 * The server holds the queue; the page only draws what it says.
 * Depends on: utils.js (appendToComposer, isAtBottom, scrollToBottom), actions.js (markFinalAnswer),
 *             render.js (appendEvent, formatUserContent, showError),
 *             stream.js (currentConversationId, lastUserMessage, setSending, startStream)
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

    if (data.status === 'queued') {
      renderQueue(data.queue);
    } else if (data.status === 'started') {
      appendEvent('user', { id: data.after_id, content: message });
      markFinalAnswer();
      lastUserMessage = message;
      startStream();
    } else {
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
      bubble.title = 'Reprendre dans la barre de saisie';
      // Safe: formatUserContent escapes all user text via escapeHtml()
      bubble.innerHTML = `${formatUserContent(entry.content)}
        <button type="button" class="queued-remove" title="Retirer" aria-label="Retirer"><i class="ri-close-line"></i></button>`;
      return bubble;
    }),
  );
  if (wasAtBottom) scrollToBottom();
}

/**
 * Take a message out of the queue; pulled back, its text goes to the composer
 */
async function takeQueued(entryId, toComposer) {
  const convId = currentConversationId;
  // Why: gone at once, so a double click does not ask for it twice; the server's `queue` event redraws the rest.
  document.querySelector(`[data-queue-id="${entryId}"]`)?.remove();
  try {
    const response = await fetch(`/api/conversations/${convId}/queue/${entryId}`, { method: 'DELETE' });
    const data = await response.json();
    if (currentConversationId !== convId) return;
    if (!response.ok) return showError(data.error || 'Message introuvable');
    if (toComposer) appendToComposer(data.content);
  } catch (error) {
    console.error('Failed to take a queued message:', error);
    if (currentConversationId === convId) showError('Erreur de connexion');
  }
}

const returnedTaken = new Set(); // Ids of returned messages already put back in the composer

/**
 * Put messages the server handed back (Stop, failed turn) in the composer once, then acknowledge them
 */
async function takeReturned(convId, entries) {
  const fresh = entries.filter((entry) => !returnedTaken.has(entry.id));
  if (!fresh.length || currentConversationId !== convId) return;
  for (const entry of fresh) {
    returnedTaken.add(entry.id);
    appendToComposer(entry.content);
  }
  try {
    await fetch(`/api/conversations/${convId}/queue/returned/ack`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: fresh.map((entry) => entry.id) }),
    });
  } catch (error) {
    console.error('Failed to acknowledge returned messages:', error);
  }
}
