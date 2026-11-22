/**
 * A conversation's stream, sending, composer state, loading UI and installation on the page.
 * The server renders the thread — finished turns in the page, the rest through the stream — as blocks this file puts
 * in place by their message ids.
 * Depends on: utils.js (autoGrow, escapeHtml, isAtBottom, scrollToBottom, appendToComposer)
 *             queue.js (queueMessage, renderQueue, takeReturned)
 *             actions.js (showPills, rebuildToc, scrollActionsToBottom, syncSidebarTabState)
 *             render.js (drawBlock, showError)
 *             permalinks.js (permalinkTarget, showPermalinkTarget, outlineSection)
 *             chat.js (parseConversationPath)
 */

let currentConversationId = null;
let conversationHold = null; // Aborted when the page leaves the conversation installed, or installs it again
let installed = Promise.resolve(); // Settles once the latest installation has the thread up to date
let brought = null; // Called once the stream being opened has brought what the page lacked, or failed to
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

  let fullMessage = message;
  if (hasFiles) {
    setSending(true);
    fullMessage = buildMessageWithFiles(message, await uploadPendingFiles(convId));
    if (currentConversationId !== convId) return;
  }

  const bubble = showPendingQuestion(message);

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
    // Why: the stream resumes after the last turn the page holds whole, known once it is installed.
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
      // Why: the server's block for the question takes the place of the bubble that bears its id.
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
 * Show a question as typed, at once; the server's block takes its place when the stream brings it
 */
function showPendingQuestion(text) {
  const chatOutput = document.getElementById('chatOutput');
  if (!chatOutput) return null;
  const bubble = document.createElement('div');
  bubble.className = 'event-block event-user';
  bubble.innerHTML = `<div class="user-text">${escapeHtml(text).replace(/\n/g, '<br>')}</div>`;
  chatOutput.appendChild(bubble);
  scrollToBottom();
  return bubble;
}

/**
 * Put in the thread the blocks the stream brings, each in place of the one that holds its first message if there is
 * one, and in the sidebar the pills that come with them
 */
function showBlocks({ blocks, pills, settled, running, status }) {
  const chatOutput = document.getElementById('chatOutput');
  if (!chatOutput) return;
  const wasAtBottom = isAtBottom();
  // Safe: the server's rendering of agent text comes out of its sanitizer (lib/answer_html.py)
  const rendered = document.createElement('template');
  rendered.innerHTML = blocks;
  const fresh = [...rendered.content.children];
  // Why: the link under the pointer may be replaced, and a removed element never sees the pointer leave.
  if (fresh.length) outlineSection(null);
  for (const block of fresh) {
    const first = block.dataset.msgId.split(' ')[0];
    const shown = chatOutput.querySelector(`:scope > [data-msg-id~="${first}"]`);
    if (shown) shown.replaceWith(block);
    else chatOutput.appendChild(block);
  }
  // Why: where the stream resumes from — the last message of the turns that will not change any more.
  chatOutput.dataset.lastId = settled;
  const charts = fresh.map(drawBlock);
  if (fresh.length) rebuildToc();
  if (pills) showPills(pills);
  if (running && turnState === 'idle') {
    setTurnState('running');
    showLoading();
  }
  const progress = document.getElementById('loadingTech');
  if (progress && status) {
    progress.textContent = status;
    progress.classList.remove('d-none');
  }
  // Keep the loading indicator at the bottom (appendChild moves existing elements)
  const loading = document.getElementById('loadingIndicator');
  if (loading) chatOutput.appendChild(loading);
  if (fresh.length && wasAtBottom) {
    scrollToBottom();
    // Why: a chart takes its height once drawn.
    if (charts.some(Boolean)) Promise.all(charts).then(() => chatOutput.isConnected && scrollToBottom());
  }
}

/**
 * Open the conversation's stream from the last turn the page holds whole: it brings what the page lacks, then
 * follows the running turn, if any, to its end. `quiet` opens it without announcing a turn, when none is known yet.
 */
function startStream({ quiet = false } = {}) {
  if (!currentConversationId) return;

  closeEventSource();

  if (!quiet) {
    setTurnState('running');
    showLoading();
  }

  const after = Number(document.getElementById('chatOutput')?.dataset.lastId) || 0;
  eventSource = new EventSource(`/api/conversations/${currentConversationId}/stream?after=${after}`);
  eventSourceConversationId = currentConversationId;

  // Blocks — reset retry counter (agent is alive and producing output)
  eventSource.addEventListener('blocks', (e) => {
    retryCount = 0;
    showBlocks(JSON.parse(e.data));
    brought?.();
  });

  eventSource.addEventListener('queue', (e) => renderQueue(JSON.parse(e.data).queue));
  eventSource.addEventListener('returned', (e) => takeReturned(eventSourceConversationId, JSON.parse(e.data).returned));

  // Why: the server rotates the stream every few minutes while the agent keeps working.
  eventSource.addEventListener('timeout', () => startStream({ quiet: turnState === 'idle' }));

  // Server heartbeat — resets retry counter during quiet periods (long tool calls)
  eventSource.addEventListener('heartbeat', () => {
    retryCount = 0;
  });

  // Completion — the server sends this when no turn is running: at the end of one, or at once when there was none
  eventSource.addEventListener('done', () => {
    closeEventSource();
    brought?.();
    if (turnState === 'idle') return;
    setTurnState('idle');

    // Reconcile all sidebar spinners (catches background conversations that finished)
    reconcileSidebarSpinners();

    signalRunFinished();

    showRepublishAlert(currentConversationId);
  });

  // Connection lost — resume from the last turn held whole. The server answers `done` at once
  // when the run ended meanwhile.
  eventSource.onerror = async () => {
    const convId = currentConversationId;
    closeEventSource();
    brought?.();

    if (retryCount >= MAX_RETRIES) {
      if (turnState === 'idle') return;
      setTurnState('idle');
      appendRecoveryMessage();
      return;
    }

    retryCount++;
    await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS * retryCount));

    if (currentConversationId === convId && !eventSource) startStream({ quiet: turnState === 'idle' });
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
  // Why: the server's last word on the turn — its answer no longer partial, the note that it was interrupted.
  startStream({ quiet: true });
  showError("Annulé par l'utilisateur");
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

// =============================================================================
// Conversation installation
// =============================================================================

/**
 * Let go of the conversation installed: what it still waits for is dropped, what holds its place is released
 */
function releaseConversation() {
  conversationHold?.abort();
  conversationHold = null;
}

/**
 * Install the scripts on a conversation the server rendered: on a page just loaded, swapped in by htmx, or put back
 * from its copy by Back or Forward. Resolves, once the thread is up to date, to whether this installation is still
 * the page's.
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
  readerMoved = false;

  // Why: a copy htmx put back also holds what the scripts added — a question not yet sent, indicators, alerts,
  // errors, the mark of a link's target. The server's blocks stay; the stream brings again those of a turn that
  // was running.
  for (const child of [...chatOutput.children]) {
    if (!child.matches('.event-block[data-msg-id]')) child.remove();
  }
  for (const marked of chatOutput.querySelectorAll('.permalink-target, .permalink-section-outline')) {
    marked.classList.remove('permalink-target', 'permalink-section-outline');
  }
  for (const block of chatOutput.children) drawBlock(block);
  rebuildToc();
  syncSidebarTabState();
  showPills('');

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

  // Why: the page may come from a copy, of htmx or of the browser, older than the conversation, and a turn may be
  // running: the stream brings what is missing, then follows that turn. A stream that stays silent holds nothing.
  await new Promise((resolve) => {
    brought = resolve;
    setTimeout(resolve, 10000);
    startStream({ quiet: true });
  });
  if (left()) return false;

  // Why: a new conversation opens with ?message=, which a reload would send again. The path keeps a permalink's
  // message and element unless that message is none of the conversation's finished answers; the hash stays. Read
  // once the thread is up to date: the answer a link names may have ended since the page was rendered. A page that
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

  return true;
}

// Start polling for sidebar spinner reconciliation if any spinners are server-rendered
document.addEventListener('DOMContentLoaded', _scheduleSpinnerPoll);
