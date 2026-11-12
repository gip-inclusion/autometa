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
  try {
    const response = await fetch(`/api/conversations/${convId}/queue/${entryId}`, { method: 'DELETE' });
    const data = await response.json();
    if (currentConversationId !== convId) return;
    if (!response.ok) return showError(data.error || 'Message introuvable');
    document.querySelector(`[data-queue-id="${entryId}"]`)?.remove();
    if (toComposer) appendToComposer(data.content);
  } catch (error) {
    console.error('Failed to take a queued message:', error);
    if (currentConversationId === convId) showError('Erreur de connexion');
  }
}
