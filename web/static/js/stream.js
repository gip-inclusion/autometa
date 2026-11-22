/**
 * SSE streaming, conversation management, composer state, and loading UI.
 * Depends on: utils.js (autoGrow, isAtBottom, scrollToBottom)
 *             queue.js (queueMessage, renderQueue, takeReturned)
 *             actions.js (streamingBlock, lastSeenId, lastAssistantBlock, resetActionsState,
 *                         removeProgressIndicator, markFinalAnswer, replayActions, rebuildToc)
 *             queue.js (renderQueue, takeReturned)
 *             render.js (appendEvent, showError, renderMermaid, renderOptions)
 *             permalinks.js (permalinkTarget, showPermalinkTarget, outlineSection)
 *             chat.js (parseConversationPath)
 */

let currentConversationId = null;
let conversationHold = null; // Aborted when the page leaves the conversation installed, or installs it again
let unreplayed = []; // Stretches of messages, [after, through], shown without the pills of their tool calls yet
let catchingUpFor = null; // The installation whose messages are being fetched for those pills
let installed = Promise.resolve(); // Settles once the latest installation has the rendered turns up to date
let outputSync = Promise.resolve(); // Requests for a conversation's rendered turns, one at a time
let readerMoved = false; // The reader has scrolled, clicked or typed since the conversation was installed

// Why: charts and late turns change heights after the page is placed; its place is held only while its reader has
// not gone elsewhere. A scroll the scripts make fires none of these.
for (const type of ['wheel', 'touchstart', 'pointerdown', 'keydown']) {
  document.addEventListener(
    type,
    () => {
      readerMoved = true;
    },
    { capture: true, passive: true },
  );
}

/**
 * Whether an id has the shape of a conversation's, as the server writes it: a UUID for the older ones, 8 characters for
 * the newer; checked before it goes into an address
 */
function isValidConversationId(id) {
  return (
    typeof id === 'string' &&
    /^(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0123456789abcdefghjkmnpqrstvwxyz]{8})$/.test(id)
  );
}

/**
 * Alert the user that a published dashboard they edited in this conversation needs republishing.
 */
async function showRepublishAlert(convId) {
  if (!isValidConversationId(convId)) return;
  const chatOutput = document.getElementById('chatOutput');
  if (!chatOutput) return;

  let drifted;
  try {
    const res = await fetch(`/api/conversations/${convId}/dashboards`);
    if (!res.ok) return;
    drifted = (await res.json()).drifted;
  } catch (_) {
    return;
  }

  // Why: retirer l'alerte périmée même quand il n'y a plus de retard (TDB republié ailleurs),
  // sinon elle resterait affichée à tort après la réponse suivante.
  document.getElementById('republish-alert')?.remove();
  if (!drifted || drifted.length === 0) return;

  const block = document.createElement('div');
  block.id = 'republish-alert';
  block.className = 'alert alert-warning mt-3';

  const intro = document.createElement('p');
  intro.className = 'mb-2';
  intro.textContent =
    drifted.length === 1
      ? 'Ce tableau de bord est publié : republiez-le pour que vos changements soient visibles en ligne.'
      : 'Ces tableaux de bord sont publiés : republiez-les pour que vos changements soient visibles en ligne.';
  block.appendChild(intro);

  for (const tdb of drifted) {
    const link = document.createElement('a');
    link.href = `/dashboards/${encodeURIComponent(tdb.slug)}/edit`;
    link.className = 'd-block';
    link.textContent = `Republier « ${tdb.title} »`;
    block.appendChild(link);
  }
  chatOutput.appendChild(block);
}

let eventSource = null;
let eventSourceConversationId = null; // Track which conversation the eventSource belongs to
let retryCount = 0;
let lastUserMessage = null;
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1000;
let turnState = 'idle'; // idle | running | cancelling
let sending = false; // This tab is uploading files or posting a message

// Track which conversation has the sidebar spinner active
let _sidebarSpinnerConvId = null;

// =============================================================================
// Sending messages
// =============================================================================

/**
 * Send a message to the agent
 */
async function sendMessage() {
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  const hasFiles = pendingFiles.length > 0;

  if (canQueue()) {
    if (!message) return input.focus();
    input.value = '';
    autoGrow(input);
    return queueMessage(currentConversationId, message);
  }

  if (!canSend()) return;

  if (!message && !hasFiles) {
    input.focus();
    return;
  }

  if (!currentConversationId) {
    setSending(true);
    try {
      const response = await fetch('/api/conversations', { method: 'POST' });
      const data = await response.json();
      currentConversationId = data.id;

      const fullMessage = buildMessageWithFiles(message, await uploadPendingFiles(data.id));
      // Redirect to conversation page (refreshes sidebar with new conversation)
      window.location.href = `/c/${data.id}?message=${encodeURIComponent(fullMessage)}`;
    } catch (error) {
      console.error('Failed to create conversation:', error);
      showError('Impossible de créer la conversation');
      setSending(false);
    }
    return;
  }

  const convId = currentConversationId;

  input.value = '';
  autoGrow(input);

  hideEmptyState();

  let fullMessage = message;
  if (hasFiles) {
    setSending(true);
    fullMessage = buildMessageWithFiles(message, await uploadPendingFiles(convId));
    if (currentConversationId !== convId) return;
  }

  const bubble = appendEvent('user', { content: fullMessage });

  lastUserMessage = fullMessage;
  retryCount = 0;

  await sendToAgent(fullMessage, { bubble, draft: message });
}

/**
 * Build the message content with file context prepended
 */
function buildMessageWithFiles(userMessage, fileContexts) {
  if (!fileContexts || fileContexts.length === 0) {
    return userMessage;
  }

  const fileSection = fileContexts.join('\n\n');
  if (!userMessage) {
    return fileSection;
  }

  return `${fileSection}\n\n---\n\n${userMessage}`;
}

/**
 * Send message to agent API and start streaming
 */
async function sendToAgent(message, { bubble, draft } = {}) {
  const convId = currentConversationId;
  setSending(true);

  try {
    // Why: the stream resumes after the last message the server rendered, known once the page is installed.
    await installed;
    if (currentConversationId !== convId) return;

    const response = await fetch(`/api/conversations/${convId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: message }),
    });

    const data = await response.json();
    if (currentConversationId !== convId) return;

    if (response.ok) {
      lastSeenId = data.after_id;
      if (bubble) bubble.dataset.msgId = data.after_id;
      startStream();
    } else if (response.status === 404) {
      await recover({ createNew: true });
    } else {
      if (data.code === 'conversation_running') {
        bubble?.remove();
        if (draft) appendToComposer(draft);
        // Why: a turn started elsewhere (another tab) — follow it, so this page can stop it or send later.
        startStream();
      }
      showError(data.error || "Erreur lors de l'envoi");
    }
  } catch (error) {
    console.error('Failed to send message:', error);
    if (currentConversationId === convId) showError('Erreur de connexion');
  }

  setSending(false);
}

// =============================================================================
// SSE streaming
// =============================================================================

/**
 * Close any existing EventSource connection
 */
function closeEventSource() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
    eventSourceConversationId = null;
  }
}

/**
 * Notify the user (tab badge + sound) that a run has finished. No-op until notify.js loads.
 */
function signalRunFinished() {
  if (typeof window.notifyRunFinished === 'function') window.notifyRunFinished();
}

/**
 * Start or resume SSE streaming for the current conversation, from the last message seen
 */
function startStream() {
  if (!currentConversationId) return;

  closeEventSource();

  setTurnState('running');

  showLoading();

  // Why: the server re-sends the message named by `after` first, so a reconnect also catches its text
  // rewritten in place; after=0 means "from the latest stored row".
  // Nothing shown yet (a first turn opened while it runs): after=1 sends the whole conversation.
  eventSource = new EventSource(`/api/conversations/${currentConversationId}/stream?after=${lastSeenId || 1}`);
  eventSourceConversationId = currentConversationId;

  // Content events — reset retry counter (agent is alive and producing output)
  ['assistant', 'tool_use', 'tool_result', 'system', 'limit'].forEach((type) => {
    eventSource.addEventListener(type, (e) => {
      retryCount = 0;
      const data = JSON.parse(e.data);
      if (typeof window.updateLoadingLastEvent === 'function') {
        if (type === 'assistant') {
          window.updateLoadingLastEvent('assistant', data);
        } else if (type === 'tool_use') {
          window.updateLoadingLastEvent('tool_use', data);
        }
      }
      appendEvent(type, data);
    });
  });

  eventSource.addEventListener('queue', (e) => renderQueue(JSON.parse(e.data).queue));
  eventSource.addEventListener('returned', (e) => takeReturned(eventSourceConversationId, JSON.parse(e.data).returned));

  // Why: messages that waited for the end of a turn arrive as questions; the answer before them is complete.
  eventSource.addEventListener('user', (e) => {
    const data = JSON.parse(e.data);
    if (!appendEvent('user', data)) return;
    markFinalAnswer();
    syncOutput();
    lastUserMessage = data.content;
  });

  // Why: the server rotates the stream every few minutes while the agent keeps working.
  eventSource.addEventListener('timeout', () => startStream());

  // Server heartbeat — resets retry counter during quiet periods (long tool calls)
  eventSource.addEventListener('heartbeat', () => {
    retryCount = 0;
  });

  // Completion — server sends this when agent finishes (needs_response cleared)
  eventSource.addEventListener('done', () => {
    closeEventSource();
    // Why: the server's rendering is about to take the place of the last block; its charts are drawn once, there.
    const last = streamingBlock;
    streamingBlock = null;
    setTurnState('idle');

    markFinalAnswer();
    syncOutput().then((running) => {
      if (running !== undefined || !last?.isConnected) return;
      renderMermaid(last);
      renderOptions(last);
    });

    // Reconcile all sidebar spinners (catches background conversations that finished)
    reconcileSidebarSpinners();

    signalRunFinished();

    showRepublishAlert(currentConversationId);
  });

  // Connection lost — resume from the last message seen. The server answers `done` at once
  // when the run ended meanwhile.
  eventSource.onerror = async () => {
    const convId = currentConversationId;
    closeEventSource();

    if (retryCount >= MAX_RETRIES) {
      setTurnState('idle');
      appendRecoveryMessage();
      return;
    }

    retryCount++;
    await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS * retryCount));

    if (currentConversationId === convId && turnState === 'running') startStream();
  };
}

// =============================================================================
// Recovery & cancel
// =============================================================================

/**
 * Show a recovery message with option to restart
 */
function appendRecoveryMessage() {
  const chatOutput = document.getElementById('chatOutput');
  if (!chatOutput) return;

  // Check scroll position BEFORE modifying DOM
  const wasAtBottom = isAtBottom();

  const block = document.createElement('div');
  block.className = 'event-block event-error';
  block.innerHTML = `
    <div>Connexion interrompue.</div>
    <button class="btn btn-sm btn-outline-primary mt-2" onclick="recover()">
      Réessayer
    </button>
    <button class="btn btn-sm btn-outline-secondary mt-2 ms-2" onclick="recover({ createNew: true })">
      Nouvelle conversation
    </button>
  `;

  chatOutput.appendChild(block);

  // Only scroll if user was at bottom
  if (wasAtBottom) {
    scrollToBottom();
  }
}

/**
 * Remove the recovery error message if visible
 */
function removeRecoveryMessage() {
  const chatOutput = document.getElementById('chatOutput');
  if (!chatOutput) return;
  const lastBlock = chatOutput.lastElementChild;
  if (lastBlock?.classList.contains('event-error')) {
    lastBlock.remove();
  }
}

/**
 * Retry the last message, optionally in a new conversation
 */
async function recover({ createNew = false } = {}) {
  if (!lastUserMessage) {
    showError('Pas de message à réessayer');
    return;
  }

  removeRecoveryMessage();

  if (createNew) {
    currentConversationId = null;
    try {
      const resp = await fetch('/api/conversations', { method: 'POST' });
      const data = await resp.json();
      currentConversationId = data.id;
    } catch (error) {
      console.error('Failed to create conversation:', error);
      showError('Impossible de créer une nouvelle conversation');
      return;
    }
  }

  retryCount = 0;
  await sendToAgent(lastUserMessage);
}

/**
 * Cancel the current stream
 */
async function cancelStream() {
  const convId = currentConversationId;
  if (!convId) return;

  setTurnState('cancelling');

  let data = {};
  try {
    const response = await fetch(`/api/conversations/${convId}/cancel`, { method: 'POST' });
    data = await response.json();
  } catch (error) {
    console.error('Failed to cancel:', error);
  }

  if (currentConversationId !== convId) return;

  closeEventSource();
  setTurnState('idle');
  appendEvent('error', { content: "Annulé par l'utilisateur" });
  // Why: only a cancelled turn hands its queue back; otherwise the messages still wait on the server.
  if (data.status === 'cancelled') renderQueue([]);
  takeReturned(convId, data.returned ?? []);
}

/**
 * Kill an agent from list/notification views
 * @param {string} convId - Conversation ID to kill
 * @param {HTMLElement|null} alertElement - Alert container to remove (for background notification)
 * @param {HTMLElement|null} cardElement - Card element to update (for conversation card)
 */
async function killAgent(convId, alertElement, cardElement) {
  try {
    const response = await fetch(`/api/conversations/${convId}/cancel`, { method: 'POST' });
    const data = await response.json();

    if (response.ok) {
      // Remove the background alert if provided
      if (alertElement) {
        alertElement.remove();
      }

      // Update the card if provided - remove running badge and kill button
      if (cardElement) {
        const runningBadge = cardElement.querySelector('.running-badge');
        const killBtn = cardElement.querySelector('.kill-agent-btn');
        if (runningBadge) runningBadge.remove();
        if (killBtn) killBtn.remove();
      }
    }
  } catch (error) {
    console.error('Failed to kill agent:', error);
  }
}

// =============================================================================
// Streaming UI state
// =============================================================================

function canSend() {
  return turnState === 'idle' && !sending;
}

function canQueue() {
  return turnState === 'running' && !sending;
}

/**
 * The only place that touches the send, upload and stop buttons
 */
function renderComposer() {
  const sendBtn = document.getElementById('chatSendBtn');
  const uploadBtn = document.getElementById('chatUploadBtn');
  const cancelBtn = document.getElementById('chatCancelBtn');
  const later = turnState !== 'idle';

  if (sendBtn) {
    sendBtn.disabled = !(canSend() || canQueue());
    sendBtn.title = later ? 'Envoyer plus tard' : 'Envoyer';
    sendBtn.setAttribute('aria-label', sendBtn.title);
    sendBtn.querySelector('i').className = later ? 'ri-chat-history-line' : 'ri-send-plane-fill';
  }
  // Why: a queued message carries text only — a file attached now would be sent with nothing.
  if (uploadBtn) uploadBtn.disabled = later;
  if (cancelBtn) {
    cancelBtn.classList.toggle('d-none', turnState === 'idle');
    cancelBtn.disabled = turnState === 'cancelling';
  }
}

function setSending(value) {
  sending = value;
  renderComposer();
}

function setTurnState(state) {
  turnState = state;

  if (state === 'idle') {
    setSidebarSpinner(_sidebarSpinnerConvId, false);
    hideLoading();
    removeProgressIndicator();
    if (streamingBlock) {
      renderMermaid(streamingBlock);
      renderOptions(streamingBlock);
      streamingBlock = null;
    }
  } else if (currentConversationId) {
    setSidebarSpinner(currentConversationId, true);
  }

  renderComposer();
}

/**
 * Show or hide the spinner icon on a sidebar conversation link.
 * Stores the original icon class in data-icon so it can be restored.
 */
function setSidebarSpinner(convId, spinning) {
  if (!convId) return;
  const link = document.querySelector(`a.nav-link-conversation[href="/c/${convId}"]`);
  if (!link) return;
  const icon = link.querySelector('i');
  if (!icon) return;

  if (spinning) {
    // Save original icon class before replacing (skip if already a spinner)
    if (!icon.dataset.icon && !icon.classList.contains('ri-spin')) {
      icon.dataset.icon = icon.className;
    }
    icon.className = 'ri-loader-4-line ri-spin';
    _sidebarSpinnerConvId = convId;
  } else {
    // Restore original icon (fallback to chat icon for server-rendered spinners)
    icon.className = icon.dataset.icon || 'ri-chat-3-line';
    delete icon.dataset.icon;
    if (_sidebarSpinnerConvId === convId) _sidebarSpinnerConvId = null;
  }
}

/**
 * Reconcile sidebar spinners with actual server state.
 * Clears spinners for conversations that are no longer running.
 */
let _spinnerPollTimer = null;

async function reconcileSidebarSpinners() {
  try {
    const resp = await fetch('/api/conversations/running');
    if (!resp.ok) return;
    const { running } = await resp.json();
    const runningSet = new Set(running);

    // Find all sidebar links that currently show a spinner
    document.querySelectorAll('a.nav-link-conversation i.ri-loader-4-line.ri-spin').forEach((icon) => {
      const link = icon.closest('a');
      if (!link) return;
      const href = link.getAttribute('href');
      const match = href?.match(/^\/c\/([^/]+)$/);
      if (!match) return;
      const convId = match[1];
      if (!runningSet.has(convId)) {
        setSidebarSpinner(convId, false);
      }
    });
  } catch {
    // Silently ignore — this is best-effort
  }

  // Keep polling while any sidebar spinner is still visible
  _scheduleSpinnerPoll();
}

function _scheduleSpinnerPoll() {
  clearTimeout(_spinnerPollTimer);
  _spinnerPollTimer = null;

  const hasSpinners = document.querySelector('a.nav-link-conversation i.ri-loader-4-line.ri-spin');
  if (hasSpinners) {
    _spinnerPollTimer = setTimeout(reconcileSidebarSpinners, 5000);
  }
}

const LOADING_BASE = 'Autometa réfléchit…';

/**
 * Dernier événement utile après « Autometa réfléchit… » (même ligne ou repli legacy).
 */
function updateLoadingLastEvent(sourceType, data) {
  let techLine = '';
  if (sourceType === 'system' && data.raw && data.raw.subtype === 'api_retry') {
    const r = data.raw;
    const attempt = r.attempt != null ? r.attempt : '?';
    const max = r.max_retries != null ? r.max_retries : '?';
    const err = r.error != null ? String(r.error) : 'erreur';
    const st = r.error_status;
    if (st != null && st !== '') {
      techLine = `Appel API · tentative ${attempt}/${max} · dernier statut ${st} · ${err}`;
    } else {
      techLine = `Appel API · tentative ${attempt}/${max} · ${err}`;
    }
  } else if (sourceType === 'tool_use' && data.content && data.content.tool) {
    techLine = `Outil · ${data.content.tool}`;
  } else if (sourceType === 'assistant') {
    techLine = 'Appel modèle · génération de la réponse';
  }

  if (!techLine) {
    return;
  }

  const techEl = document.getElementById('loadingTech');
  const baseEl = document.getElementById('loadingBase');
  if (techEl && baseEl) {
    baseEl.textContent = LOADING_BASE;
    techEl.textContent = techLine;
    techEl.classList.remove('d-none');
    return;
  }

  const statusEl = document.getElementById('loadingStatus');
  if (statusEl) {
    statusEl.textContent = `${LOADING_BASE} — ${techLine}`;
    return;
  }

  const legacyDebug = document.getElementById('loadingDebug');
  if (legacyDebug) {
    legacyDebug.textContent = ` — ${techLine}`;
    legacyDebug.classList.remove('d-none');
    return;
  }

  const loading = document.getElementById('loadingIndicator');
  if (!loading) {
    return;
  }
  let fb = document.getElementById('loadingStatusFallback');
  if (!fb) {
    fb = document.createElement('div');
    fb.id = 'loadingStatusFallback';
    fb.className = 'loading-tech';
    fb.setAttribute('aria-live', 'polite');
    loading.appendChild(fb);
  }
  fb.textContent = `${LOADING_BASE} — ${techLine}`;
}

window.updateLoadingLastEvent = updateLoadingLastEvent;

/**
 * Show loading indicator
 */
function showLoading() {
  const chatOutput = document.getElementById('chatOutput');
  if (!chatOutput) return;

  // Check scroll position BEFORE modifying DOM
  const wasAtBottom = isAtBottom();

  // Remove existing loading
  hideLoading();

  const loading = document.createElement('div');
  loading.className = 'loading-indicator flex-wrap';
  loading.id = 'loadingIndicator';
  loading.innerHTML = `
    <div class="spinner"></div>
    <div class="loading-indicator-text">
      <span id="loadingBase" class="loading-base">${LOADING_BASE}</span>
      <span id="loadingTech" class="loading-tech d-none" aria-live="polite"></span>
    </div>
  `;

  chatOutput.appendChild(loading);

  // Only scroll if user was at bottom
  if (wasAtBottom) {
    scrollToBottom();
  }
}

/**
 * Hide loading indicator
 */
function hideLoading() {
  const loading = document.getElementById('loadingIndicator');
  if (loading) loading.remove();
}

/**
 * Hide empty state
 */
function hideEmptyState() {
  const emptyState = document.getElementById('emptyState');
  if (emptyState) emptyState.style.display = 'none';
}

// =============================================================================
// Conversation installation
// =============================================================================

/**
 * Bring the turns the server has rendered since the last one shown, in place of the blocks drawn from the stream:
 * the page then shows what a reload would. Resolves to whether a turn is running, undefined when it could not ask.
 */
function syncOutput(scroll = true) {
  // Why: read now — by the time its turn comes, the page may be installed on another conversation.
  const hold = conversationHold;
  const convId = currentConversationId;
  outputSync = outputSync.then(() => fetchRenderedTurns(hold, convId, scroll));
  return outputSync;
}

/**
 * Let go of the conversation installed: what it still waits for is dropped, what holds its place is released
 */
function releaseConversation() {
  conversationHold?.abort();
  conversationHold = null;
}

function firstMessageId(block) {
  return block.dataset.msgId?.split(' ')[0];
}

function moveFootnotes(from, to) {
  const footnotes = from.querySelector(':scope > .action-footnotes');
  if (footnotes) to.appendChild(footnotes);
  if (from === lastAssistantBlock) lastAssistantBlock = to;
}

async function fetchRenderedTurns(hold, convId, scroll) {
  const chatOutput = document.getElementById('chatOutput');
  if (!hold || hold.signal.aborted || !chatOutput || !isValidConversationId(convId)) return;
  const left = () => hold.signal.aborted || !chatOutput.isConnected;
  // Why: links and exact rendering are an extra; whatever fails here leaves the blocks the stream drew.
  try {
    const shown = Number(chatOutput.dataset.lastId) || 0;
    // Why: a request left without an answer must not hold what waits for it — the stream, the next message.
    const response = await fetch(`/api/conversations/${convId}/blocks?after=${shown}`, {
      signal: AbortSignal.timeout(10000),
    });
    if (!response.ok || left()) return;
    const { html, last_id: lastId, running } = await response.json();
    if (left()) return;
    // Safe: the server's rendering of agent text comes out of its sanitizer (lib/answer_html.py)
    const rendered = document.createElement('template');
    rendered.innerHTML = html;
    const wasAtBottom = isAtBottom();
    // Why: the link under the pointer is about to be replaced, and a removed element never sees the pointer leave.
    outlineSection(null);
    // Why: an answer the server already gave may have grown by a message since; it comes again whole, in its place.
    const fresh = [...rendered.content.children];
    const added = fresh.filter((block) => {
      const given = chatOutput.querySelector(`:scope > :not([data-live])[data-msg-id~="${firstMessageId(block)}"]`);
      if (!given) return true;
      given.replaceWith(block);
      moveFootnotes(given, block);
      return false;
    });
    const live = [...chatOutput.querySelectorAll(':scope > [data-live]')];
    const covered = live.filter((block) => Number(firstMessageId(block)) <= lastId);
    const replaced = covered.length ? live.slice(live.indexOf(covered[0]), live.indexOf(covered.at(-1)) + 1) : [];
    if (replaced.length) replaced[0].before(...added);
    else if (live.length) live[0].before(...added);
    else chatOutput.append(...added);
    for (const block of replaced) {
      block.remove();
      const first = firstMessageId(block);
      const successor = first && chatOutput.querySelector(`:scope > [data-msg-id~="${first}"]`);
      if (successor) moveFootnotes(block, successor);
    }
    // Why: a turn relaunched on its old question leaves the server's mark before a question already shown.
    chatOutput.dataset.lastId = Math.max(shown, lastId);
    chatOutput.toggleAttribute('data-running', running);
    showThrough(Number(chatOutput.dataset.lastId));
    // Why: pills that could not be built earlier are tried again each time the turns are brought.
    catchUpActions();
    const charts = fresh
      .filter((block) => block.matches('.event-assistant'))
      .map((block) => {
        renderOptions(block);
        return block.querySelector('code.language-mermaid') && renderMermaid(block);
      });
    if (fresh.length) rebuildToc();
    // Keep the loading indicator at the bottom (appendChild moves existing elements)
    const loading = document.getElementById('loadingIndicator');
    if (loading) chatOutput.appendChild(loading);
    if (scroll && fresh.length && wasAtBottom) {
      scrollToBottom();
      // Why: a chart takes its height once drawn.
      if (charts.some(Boolean)) Promise.all(charts).then(() => left() || scrollToBottom());
    }
    return running;
  } catch (error) {
    console.error('Failed to bring the rendered turns:', error);
  }
}

/**
 * Count the messages up to `id` as shown. The stream will not bring those it had not yet, so the pills of their tool
 * calls are built from the conversation's messages.
 */
function showThrough(id) {
  if (id <= lastSeenId) return;
  // Why: a call the stream brought without its result yet is built again with it, from the messages.
  unreplayed.push([pendingToolUseIds.length ? pendingToolUseIds[0] - 1 : lastSeenId, id]);
  pendingToolUses = [];
  pendingToolUseIds = [];
  lastSeenId = id;
  catchUpActions();
}

async function catchUpActions() {
  const hold = conversationHold;
  const convId = currentConversationId;
  if (!hold || catchingUpFor === hold || !unreplayed.length) return;
  catchingUpFor = hold;
  const gaps = [...unreplayed];
  try {
    // Why: megabytes of tool outputs at times, on any link: no time limit, since nothing but the pills waits for
    // them; given up when the page leaves the conversation.
    const response = await fetch(`/api/conversations/${convId}`, { signal: hold.signal });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const conv = await response.json();
    if (hold.signal.aborted) return;
    replayActions(conv.messages, gaps);
    // Why: only now are they built; a stretch whose messages could not be read is tried again at the next turns.
    unreplayed = unreplayed.filter((gap) => !gaps.includes(gap));
    // Why: a page being installed has no stream to tell it what waits or was handed back; once it has one, the
    // stream knows better than these messages, read before it started.
    if (gaps[0][0] === 0 && !eventSource) {
      renderQueue(conv.queue);
      takeReturned(conv.id, conv.returned);
    }
  } catch (error) {
    if (!hold.signal.aborted) console.error('Failed to load conversation:', error);
    return;
  } finally {
    if (catchingUpFor === hold) catchingUpFor = null;
  }
  catchUpActions();
}

/**
 * Install the scripts on a conversation the server rendered: on a page just loaded, swapped in by htmx, or put back
 * from its copy by Back or Forward. Resolves, once the rendered turns are up to date, to whether this installation
 * is still the page's.
 */
function installConversation(convId) {
  // Why: whatever goes wrong, the page must stay usable: a message waits for this promise before it leaves.
  installed = install(convId).catch((error) => {
    console.error('Failed to install the conversation:', error);
    return false;
  });
  return installed;
}

async function install(convId) {
  const chatOutput = document.getElementById('chatOutput');
  if (!chatOutput || !isValidConversationId(convId)) return false;
  releaseConversation();
  const hold = new AbortController();
  conversationHold = hold;
  // Why: while it waits, the page may move to another conversation or to a page without one.
  const left = () => hold.signal.aborted || !chatOutput.isConnected;

  closeEventSource();
  currentConversationId = convId;
  resetActionsState();
  readerMoved = false;
  unreplayed = [];
  // Why: a request another conversation still waits for must not hold this one.
  outputSync = Promise.resolve();

  // Why: a copy htmx put back also holds what the scripts drew — blocks of a turn then running, indicators, alerts,
  // references whose clicks went with the page, the mark of a link's target. The server's blocks stay.
  for (const child of [...chatOutput.children]) {
    if (!child.matches('.event-block[data-msg-id]:not([data-live])')) child.remove();
  }
  for (const footnotes of chatOutput.querySelectorAll('.action-footnotes')) footnotes.remove();
  for (const marked of chatOutput.querySelectorAll('.permalink-target, .permalink-section-outline')) {
    marked.classList.remove('permalink-target', 'permalink-section-outline');
  }
  for (const block of chatOutput.querySelectorAll(':scope > .event-assistant')) {
    renderOptions(block);
    renderMermaid(block);
  }
  rebuildToc();

  const hash = window.location.hash;
  const opened = parseConversationPath(window.location.pathname);
  const message = opened?.conversation === convId && opened.message;
  const place = () => {
    if (left()) return null;
    const target = message ? permalinkTarget(message, opened.anchor) : null;
    // Why: a reader gone elsewhere stays there; what the link names is marked all the same.
    if (readerMoved) {
      if (target?.getClientRects().length) target.classList.add('permalink-target');
      return target;
    }
    if (target && showPermalinkTarget(target)) return target;
    const section = hash && document.getElementById(hash.substring(1));
    if (section) section.scrollIntoView({ block: 'start' });
    else {
      scrollToBottom();
      scrollActionsToBottom();
    }
    return target;
  };
  // Why: the page arrives placed and held there by its template (explorations.html); from here on it is these
  // scripts that mark its target and hold its place, as charts are drawn and late turns come, until its reader moves.
  const shown = chatOutput.childElementCount;
  const placed = place();
  chatOutput.parentElement.hold?.abort();
  const pin = new ResizeObserver(place);
  pin.observe(chatOutput);
  hold.signal.addEventListener('abort', () => pin.disconnect());

  // Why: the page may come from a copy, of htmx or of the browser, older than the conversation.
  const running = await syncOutput(false);
  if (left()) return false;
  // Why: when the server could not be asked again, the page it rendered still says where it stopped.
  showThrough(Number(chatOutput.dataset.lastId) || 0);

  // Why: a new conversation opens with ?message=, which a reload would send again. The path keeps a permalink's
  // message and element unless that message is none of the conversation's finished answers; the hash stays. Read
  // once the turns are up to date: the answer a link names may have ended since the page was rendered. A page that
  // was up to date stays where its reader may have moved it meanwhile.
  const target = chatOutput.childElementCount === shown ? placed : place();
  // Why: htmx restores on Back/Forward only an entry whose state it marked — replacing the state would unmark it.
  window.history.replaceState(window.history.state, '', `${target ? window.location.pathname : `/c/${convId}`}${hash}`);
  if (message && !target) showError('Ce lien ne correspond à aucune réponse de cette conversation.');

  // Reconcile sidebar spinners on every conversation load
  reconcileSidebarSpinners();

  // Why: au chargement d'une conversation, réafficher (ou retirer) l'alerte de republication
  // selon l'état réel du serveur — sinon elle ne réapparaît qu'à la prochaine réponse.
  showRepublishAlert(convId);

  if (running ?? 'running' in chatOutput.dataset) startStream();

  return true;
}

/**
 * Start a fresh conversation (clear current state)
 */
function startFreshConversation() {
  closeEventSource();
  currentConversationId = null;
  lastUserMessage = null;
  retryCount = 0;

  // Reset actions sidebar
  resetActionsState();

  // Deselect active conversation in sidebar
  document.querySelectorAll('.nav-sublink.active').forEach((el) => {
    el.classList.remove('active');
  });

  // Clear chat output
  const chatOutput = document.getElementById('chatOutput');
  if (chatOutput) {
    chatOutput.innerHTML = `
      <div class="empty-state" id="emptyState">
        <i class="ri-chat-3-line ri-4x text-disabled mb-3"></i>
        <p class="mb-0 text-muted">Posez une question pour commencer</p>
        <p class="small text-muted">Ex : « Combien de visiteurs sur les Emplois en décembre ? »</p>
      </div>
    `;
  }

  // Update URL
  window.history.replaceState({}, '', '/c/new');

  // Focus input
  const input = document.getElementById('chatInput');
  if (input) {
    input.focus();
  }
}

// Start polling for sidebar spinner reconciliation if any spinners are server-rendered
document.addEventListener('DOMContentLoaded', _scheduleSpinnerPoll);
