/**
 * Matometa Chat Interface
 * Handles conversation creation, SSE streaming, and UI updates
 */

let currentConversationId = null;
let eventSource = null;

/**
 * Initialize the chat interface
 */
function initChat() {
  const input = document.getElementById('chatInput');
  const sendBtn = document.getElementById('chatSendBtn');
  const cancelBtn = document.getElementById('chatCancelBtn');
  const hideToolsToggle = document.getElementById('hideToolsToggle');
  const chatOutput = document.getElementById('chatOutput');

  if (!input || !sendBtn) return;

  // Auto-grow textarea
  input.addEventListener('input', () => autoGrow(input));

  // Send on button click
  sendBtn.addEventListener('click', () => sendMessage());

  // Send on Enter (Shift+Enter for newline)
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Cancel button
  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => cancelStream());
  }

  // Hide tools toggle
  if (hideToolsToggle && chatOutput) {
    hideToolsToggle.addEventListener('change', (e) => {
      chatOutput.classList.toggle('hide-tools', e.target.checked);
    });
  }
}

/**
 * Auto-grow textarea to fit content
 */
function autoGrow(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
}

/**
 * Send a message to the agent
 */
async function sendMessage() {
  const input = document.getElementById('chatInput');
  const message = input.value.trim();

  if (!message) {
    input.focus();
    return;
  }

  // Create conversation if needed
  if (!currentConversationId) {
    try {
      const response = await fetch('/api/conversations', { method: 'POST' });
      const data = await response.json();
      currentConversationId = data.id;
    } catch (error) {
      console.error('Failed to create conversation:', error);
      showError('Impossible de creer la conversation');
      return;
    }
  }

  // Clear input
  input.value = '';
  autoGrow(input);

  // Hide empty state
  hideEmptyState();

  // Show user message
  appendEvent('user', { content: message });

  // Send message to API
  try {
    const response = await fetch(`/api/conversations/${currentConversationId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: message }),
    });

    const data = await response.json();

    if (!response.ok) {
      showError(data.error || 'Erreur lors de l\'envoi');
      return;
    }

    // Start streaming
    startStream();

  } catch (error) {
    console.error('Failed to send message:', error);
    showError('Erreur de connexion');
  }
}

/**
 * Start SSE streaming for the current conversation
 */
function startStream() {
  if (!currentConversationId) return;

  setStreamingState(true);

  // Show loading indicator
  showLoading();

  // Connect to SSE endpoint
  eventSource = new EventSource(`/api/conversations/${currentConversationId}/stream`);

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
  eventSource.addEventListener('done', () => {
    eventSource.close();
    eventSource = null;
    setStreamingState(false);
    hideLoading();
  });

  // Handle errors
  eventSource.onerror = (e) => {
    console.error('SSE error:', e);
    eventSource.close();
    eventSource = null;
    setStreamingState(false);
    hideLoading();
    showError('Connexion interrompue');
  };
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
  appendEvent('system', { content: 'Annule par l\'utilisateur' });
}

/**
 * Append an event to the chat output
 */
function appendEvent(type, data) {
  const chatOutput = document.getElementById('chatOutput');
  if (!chatOutput) return;

  const block = document.createElement('div');
  block.className = `event-block event-${type}`;

  if (type === 'user') {
    block.innerHTML = escapeHtml(data.content);
  } else if (type === 'assistant') {
    block.innerHTML = formatAssistantContent(data.content);
  } else if (type === 'tool_use') {
    block.innerHTML = formatToolUse(data.content);
  } else if (type === 'tool_result') {
    block.innerHTML = formatToolResult(data.content);
  } else if (type === 'system' || type === 'error') {
    block.innerHTML = escapeHtml(data.content || '');
  }

  chatOutput.appendChild(block);
  scrollToBottom();
}

/**
 * Format assistant content (simple markdown-ish)
 */
function formatAssistantContent(content) {
  if (!content) return '';

  let html = escapeHtml(content);

  // Code blocks
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Bold
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  // Line breaks
  html = html.replace(/\n/g, '<br>');

  return html;
}

/**
 * Format tool use event
 */
function formatToolUse(content) {
  if (!content) return '';

  const tool = content.tool || 'Unknown';
  const input = content.input || {};

  let html = `<div class="tool-name">${escapeHtml(tool)}</div>`;

  if (typeof input === 'object') {
    const inputStr = JSON.stringify(input, null, 2);
    html += `<div class="tool-content">${escapeHtml(inputStr)}</div>`;
  } else {
    html += `<div class="tool-content">${escapeHtml(String(input))}</div>`;
  }

  return html;
}

/**
 * Format tool result event
 */
function formatToolResult(content) {
  if (!content) return '';

  const tool = content.tool || '';
  const output = content.output || '';

  let html = '';
  if (tool) {
    html += `<div class="tool-name">${escapeHtml(tool)}</div>`;
  }

  // Truncate very long outputs
  let outputStr = typeof output === 'object' ? JSON.stringify(output, null, 2) : String(output);
  if (outputStr.length > 2000) {
    outputStr = outputStr.substring(0, 2000) + '\n... (tronque)';
  }

  html += `<div class="tool-content">${escapeHtml(outputStr)}</div>`;

  return html;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

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
}

/**
 * Show loading indicator
 */
function showLoading() {
  const chatOutput = document.getElementById('chatOutput');
  if (!chatOutput) return;

  // Remove existing loading
  hideLoading();

  const loading = document.createElement('div');
  loading.className = 'loading-indicator';
  loading.id = 'loadingIndicator';
  loading.innerHTML = '<div class="spinner"></div> Matometa reflechit...';

  chatOutput.appendChild(loading);
  scrollToBottom();
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

/**
 * Show error message
 */
function showError(message) {
  appendEvent('error', { content: message });
}

/**
 * Scroll chat to bottom
 */
function scrollToBottom() {
  const chatOutput = document.getElementById('chatOutput');
  if (chatOutput) {
    chatOutput.scrollTop = chatOutput.scrollHeight;
  }
}
