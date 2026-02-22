/**
 * SSE streaming, conversation management, and loading UI.
 * Depends on: utils.js (autoGrow, isAtBottom, scrollToBottom)
 *             actions.js (streamingBlock, streamingText, resetActionsState,
 *                         removeProgressIndicator, markFinalAnswer,
 *                         markFinalAnswersInConversation, addFootnotesToLastAssistant)
 *             render.js (appendEvent, showError, renderMermaid, renderOptions)
 */

let currentConversationId = null;
let eventSource = null;
let eventSourceConversationId = null;  // Track which conversation the eventSource belongs to
let retryCount = 0;
let lastUserMessage = null;
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1000;

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

  if (!message && !hasFiles) {
    input.focus();
    return;
  }

  // Create conversation if needed
  if (!currentConversationId) {
    try {
      const response = await fetch('/api/conversations', { method: 'POST' });
      const data = await response.json();
      currentConversationId = data.id;

      // If we have pending files, we need to upload them first, then redirect
      if (hasFiles) {
        // Upload files to the new conversation
        const fileContexts = await uploadPendingFiles();
        const fullMessage = buildMessageWithFiles(message, fileContexts);

        // Redirect with the full message
        window.location.href = `/explorations/${currentConversationId}?message=${encodeURIComponent(fullMessage)}`;
      } else {
        // Redirect to conversation page (refreshes sidebar with new conversation)
        window.location.href = `/explorations/${currentConversationId}?message=${encodeURIComponent(message)}`;
      }
      return;
    } catch (error) {
      console.error('Failed to create conversation:', error);
      showError('Impossible de créer la conversation');
      return;
    }
  }

  // Clear input
  input.value = '';
  autoGrow(input);

  // Hide empty state
  hideEmptyState();

  // Upload pending files first (if any)
  let fullMessage = message;
  if (hasFiles) {
    setStreamingState(true);  // Show loading during upload
    const fileContexts = await uploadPendingFiles();
    fullMessage = buildMessageWithFiles(message, fileContexts);
    setStreamingState(false);
  }

  // Show user message (with file info if any)
  appendEvent('user', { content: fullMessage });

  // Save message for potential retry
  lastUserMessage = fullMessage;
  retryCount = 0;

  // Send message to API
  await sendToAgent(fullMessage);
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
async function sendToAgent(message) {
  try {
    const response = await fetch(`/api/conversations/${currentConversationId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: message }),
    });

    const data = await response.json();

    if (!response.ok) {
      // If conversation not found, try to recover
      if (response.status === 404) {
        await recoverConversation(message);
        return;
      }
      showError(data.error || 'Erreur lors de l\'envoi');
      return;
    }

    // Start streaming from after the user message we just sent
    startStream(data.after_id || 0);

  } catch (error) {
    console.error('Failed to send message:', error);
    showError('Erreur de connexion');
  }
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
 * Return the ID of the last message the client already has from a conv payload.
 */
function lastLoadedMsgId(conv) {
  return conv?.messages?.length
    ? conv.messages[conv.messages.length - 1].id
    : 0;
}

/**
 * Start SSE streaming for the current conversation
 */
function startStream(afterMsgId = 0) {
  if (!currentConversationId) return;

  // Close any existing connection first
  closeEventSource();

  setStreamingState(true);

  // Show loading indicator
  showLoading();

  // Connect to SSE endpoint (after= tells server where client left off)
  const afterParam = afterMsgId ? `?after=${afterMsgId}` : '';
  eventSource = new EventSource(`/api/conversations/${currentConversationId}/stream${afterParam}`);
  eventSourceConversationId = currentConversationId;

  // Handle different event types
  const eventTypes = ['assistant', 'tool_use', 'tool_result', 'system', 'error'];
  eventTypes.forEach(type => {
    eventSource.addEventListener(type, (e) => {
      const data = JSON.parse(e.data);
      appendEvent(type, data);

      // Only hide loading when we get actual content (assistant response or error)
      if (type === 'assistant' || type === 'error') {
        hideLoading();
      }
    });
  });

  // Handle completion
  eventSource.addEventListener('done', async (e) => {
    eventSource.close();
    eventSource = null;
    eventSourceConversationId = null;
    setStreamingState(false);
    hideLoading();
    removeProgressIndicator();

    // Check if server says to reload (e.g., after wait_stream reconnection)
    let shouldReload = retryCount > 0;
    try {
      const data = JSON.parse(e.data || '{}');
      if (data.reload) shouldReload = true;
    } catch {}

    if (shouldReload && currentConversationId) {
      await loadConversation(currentConversationId, { autoStream: false });
    }

    markFinalAnswer();
  });

  // Handle errors
  eventSource.onerror = async (e) => {
    console.error('SSE error:', e);
    eventSource.close();
    eventSource = null;
    eventSourceConversationId = null;

    // Try to retry if we haven't exceeded max retries
    if (retryCount < MAX_RETRIES && lastUserMessage) {
      retryCount++;
      console.log(`Retrying (${retryCount}/${MAX_RETRIES})...`);

      // Wait before retrying (exponential backoff)
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY_MS * retryCount));

      // Check if conversation still exists, recover if not
      try {
        const checkResponse = await fetch(`/api/conversations/${currentConversationId}`);
        if (checkResponse.status === 404) {
          console.log('Conversation lost, recovering...');
          await recoverConversation(lastUserMessage);
          return;
        }
      } catch (err) {
        console.error('Failed to check conversation:', err);
      }

      // Conversation exists — reload from DB to catch missed events, then retry stream
      const reloaded = await loadConversation(currentConversationId, { autoStream: false });
      startStream(lastLoadedMsgId(reloaded));
      return;
    }

    // Max retries exceeded — but check if agent is still running before giving up
    try {
      const checkResponse = await fetch(`/api/conversations/${currentConversationId}`);
      if (checkResponse.ok) {
        const conv = await checkResponse.json();
        if (conv.is_running) {
          // Agent still running, reset retries and keep waiting
          console.log('Agent still running, resetting retries...');
          retryCount = 0;
          const reloaded = await loadConversation(currentConversationId, { autoStream: false });
          startStream(lastLoadedMsgId(reloaded));
          return;
        }
      }
    } catch (err) {
      console.error('Failed to check if agent is running:', err);
    }

    // Agent truly stopped or unreachable
    setStreamingState(false);
    hideLoading();
    removeProgressIndicator();

    // Show error with recovery option
    appendRecoveryMessage();
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
    <button class="btn btn-sm btn-outline-primary mt-2" onclick="retryLastMessage()">
      Réessayer
    </button>
    <button class="btn btn-sm btn-outline-secondary mt-2 ms-2" onclick="startNewConversation()">
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
 * Retry the last message
 */
async function retryLastMessage() {
  if (!lastUserMessage) {
    showError('Pas de message à réessayer');
    return;
  }

  // Remove the recovery message
  const chatOutput = document.getElementById('chatOutput');
  const lastBlock = chatOutput.lastElementChild;
  if (lastBlock && lastBlock.classList.contains('event-error')) {
    lastBlock.remove();
  }

  retryCount = 0;
  setStreamingState(true);
  showLoading();

  // Try with existing conversation first, recover if needed
  await sendToAgent(lastUserMessage);
}

/**
 * Start a completely new conversation
 */
async function startNewConversation() {
  // Remove the recovery message
  const chatOutput = document.getElementById('chatOutput');
  const lastBlock = chatOutput.lastElementChild;
  if (lastBlock && lastBlock.classList.contains('event-error')) {
    lastBlock.remove();
  }

  // Reset state
  currentConversationId = null;
  retryCount = 0;

  // Create new conversation
  try {
    const response = await fetch('/api/conversations', { method: 'POST' });
    const data = await response.json();
    currentConversationId = data.id;

    // Re-send the last message
    if (lastUserMessage) {
      setStreamingState(true);
      showLoading();
      await sendToAgent(lastUserMessage);
    }
  } catch (error) {
    console.error('Failed to create conversation:', error);
    showError('Impossible de créer une nouvelle conversation');
  }
}

/**
 * Recover from a lost conversation by creating a new one
 */
async function recoverConversation(message) {
  console.log('Conversation not found, creating new one...');

  // Reset conversation
  currentConversationId = null;

  try {
    const response = await fetch('/api/conversations', { method: 'POST' });
    const data = await response.json();
    currentConversationId = data.id;

    // Re-send the message
    await sendToAgent(message);
  } catch (error) {
    console.error('Failed to recover conversation:', error);
    setStreamingState(false);
    hideLoading();
    showError('Impossible de reprendre la conversation');
  }
}

/**
 * Cancel the current stream
 */
async function cancelStream() {
  if (!currentConversationId) return;

  try {
    await fetch(`/api/conversations/${currentConversationId}/cancel`, { method: 'POST' });
  } catch (error) {
    console.error('Failed to cancel:', error);
  }

  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }

  setStreamingState(false);
  hideLoading();
  removeProgressIndicator();
  appendEvent('error', { content: 'Annulé par l\'utilisateur' });
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

/**
 * Show/hide streaming state
 */
function setStreamingState(streaming) {
  const sendBtn = document.getElementById('chatSendBtn');
  const cancelBtn = document.getElementById('chatCancelBtn');
  const input = document.getElementById('chatInput');

  if (sendBtn) sendBtn.style.display = streaming ? 'none' : 'flex';
  if (cancelBtn) cancelBtn.style.display = streaming ? 'flex' : 'none';
  if (input) input.disabled = streaming;

  // Finalize streaming block when streaming ends
  if (!streaming && streamingBlock) {
    renderMermaid(streamingBlock);
    renderOptions(streamingBlock);
    streamingBlock = null;
    streamingText = '';
  }
}

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
  loading.className = 'loading-indicator';
  loading.id = 'loadingIndicator';
  loading.innerHTML = '<div class="spinner"></div> Matometa réfléchit…';

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
// Conversation loading
// =============================================================================

/**
 * Load an existing conversation by ID
 */
async function loadConversation(convId, { autoStream = true } = {}) {
  // Close any existing EventSource before loading new conversation
  closeEventSource();

  // Reset actions sidebar state
  resetActionsState();

  try {
    const response = await fetch(`/api/conversations/${convId}`);
    if (!response.ok) {
      console.error('Failed to load conversation:', response.status);
      return;
    }

    const conv = await response.json();
    currentConversationId = conv.id;

    // Clear loading indicator
    const loadingIndicator = document.getElementById('loadingConversation');
    if (loadingIndicator) {
      loadingIndicator.remove();
    }

    // Hide empty state
    hideEmptyState();

    // Render existing messages
    const chatOutput = document.getElementById('chatOutput');
    if (chatOutput && conv.messages) {
      // Clear existing content first
      chatOutput.innerHTML = '';

      for (const msg of conv.messages) {
        if (msg.type === 'user') {
          appendEvent('user', { content: msg.content, timestamp: msg.timestamp });
        } else if (msg.type === 'assistant') {
          appendEvent('assistant', { content: msg.content });
        } else if (msg.type === 'tool_use') {
          try {
            const content = JSON.parse(msg.content);
            appendEvent('tool_use', { content });
          } catch {
            appendEvent('tool_use', { content: { tool: 'unknown', input: msg.content } });
          }
        } else if (msg.type === 'tool_result') {
          try {
            const content = JSON.parse(msg.content);
            appendEvent('tool_result', { content });
          } catch {
            appendEvent('tool_result', { content: { output: msg.content } });
          }
        } else if (msg.type === 'report') {
          appendEvent('report', { content: msg.content });
        }
      }

      // Add footnotes to the last assistant message
      addFootnotesToLastAssistant();

      // Mark final answers
      markFinalAnswersInConversation();

      // Reset streaming state after DB load — these are static events, not a live stream
      streamingBlock = null;
      streamingText = '';
    }

    // Update URL without reload (preserve hash if present)
    const hash = window.location.hash;
    window.history.replaceState({}, '', `/explorations/${convId}${hash}`);

    // Scroll handling: if URL has a section hash, scroll to it; otherwise scroll to bottom
    // Use longer delay to ensure DOM is fully rendered
    setTimeout(() => {
      if (hash) {
        const element = document.getElementById(hash.substring(1));
        if (element) {
          // Instant scroll on page load (no smooth)
          element.scrollIntoView({ block: 'start' });
          return;
        }
      }
      // Default: scroll to bottom
      scrollToBottom();
      window.scrollTo(0, document.body.scrollHeight);
    }, 100);

    // If conversation is running, resume the stream (unless caller handles it)
    if (autoStream && conv.is_running) {
      console.log('Conversation is running, resuming stream...');
      const lastMsgId = lastLoadedMsgId(conv);
      startStream(lastMsgId);
    }

    return conv;

  } catch (error) {
    console.error('Failed to load conversation:', error);
  }
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
  document.querySelectorAll('.nav-sublink.active').forEach(el => el.classList.remove('active'));

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
  window.history.replaceState({}, '', '/explorations/new');

  // Focus input
  const input = document.getElementById('chatInput');
  if (input) {
    input.focus();
  }
}
