/**
 * Message rendering: appendEvent dispatcher, format functions, mermaid/options.
 * Depends on: utils.js (escapeHtml, isAtBottom, scrollToBottom, formatFileSize)
 *             actions.js (streamingBlock, assistantParts, lastSeenId, pendingToolUses, lastAssistantBlock,
 *                         currentTurnActions, createAndAppendAction, addFootnotesToLastAssistant,
 *                         scanHeadingsForToc, rebuildToc)
 */

/**
 * Update token display with new usage data
 */
function updateTokenDisplay(usage) {
  const tokenDisplay = document.getElementById('tokenDisplay');
  const tokenCount = document.getElementById('tokenCount');
  if (!tokenDisplay || !tokenCount) return;

  // Get current values from data attributes
  let currentInput = parseInt(tokenDisplay.dataset.input, 10) || 0;
  let currentOutput = parseInt(tokenDisplay.dataset.output, 10) || 0;

  // Add new usage
  const newInput = usage.input_tokens || 0;
  const newOutput = usage.output_tokens || 0;
  currentInput += newInput;
  currentOutput += newOutput;

  // Update data attributes
  tokenDisplay.dataset.input = currentInput;
  tokenDisplay.dataset.output = currentOutput;

  // Update display
  const total = currentInput + currentOutput;
  tokenCount.textContent = total.toLocaleString();
  tokenDisplay.title = `Tokens utilisés: ${currentInput.toLocaleString()} entrée, ${currentOutput.toLocaleString()} sortie`;

  // Show if hidden
  tokenDisplay.classList.remove('d-none');
}

function renderAssistantBlock(block) {
  const text = block.dataset.msgId
    .split(' ')
    .map((id) => assistantParts.get(id))
    .join('');
  const reportInfo = detectReport(text);
  const footnotes = block.querySelector('.action-footnotes');
  block.dataset.rawContent = text;
  block.classList.toggle('event-report', Boolean(reportInfo));
  block.innerHTML = reportInfo ? formatReport(text, reportInfo) : formatAssistantContent(text);
  if (footnotes) block.appendChild(footnotes);
}

function updateAssistantBlock(block, partId, content) {
  const wasAtBottom = isAtBottom();
  assistantParts.set(partId, content);
  renderAssistantBlock(block);
  if (block.isConnected && block.querySelector('h2')) rebuildToc();
  if (block !== streamingBlock) {
    renderMermaid(block);
    renderOptions(block);
  }
  if (wasAtBottom) scrollToBottom();
}

/**
 * Append an event to the chat output, or update the block that already shows it
 */
function appendEvent(type, data) {
  const chatOutput = document.getElementById('chatOutput');
  if (!chatOutput) return;

  if (data.id) {
    const known = chatOutput.querySelector(`[data-msg-id~="${data.id}"]`);
    if (type === 'assistant' && known) {
      if (assistantParts.get(String(data.id)) !== data.content) {
        updateAssistantBlock(known, String(data.id), data.content);
      }
      return;
    }
    if (data.id <= lastSeenId) return;
    lastSeenId = data.id;
  }

  // System events: check for usage data, then skip display
  if (type === 'system') {
    if (data.raw?.usage) {
      updateTokenDisplay(data.raw.usage);
    }
    if (typeof window.updateLoadingLastEvent === 'function') {
      window.updateLoadingLastEvent('system', data);
    }
    return;
  }

  // Non-assistant event ends the streaming accumulation
  if (type !== 'assistant' && streamingBlock) {
    renderMermaid(streamingBlock);
    renderOptions(streamingBlock);
    streamingBlock = null;
  }

  // Tool events: add to sidebar instead of main chat
  if (type === 'tool_use') {
    // Queue tool_use - supports parallel tool calls
    pendingToolUses.push(data.content);
    return;
  }

  if (type === 'tool_result') {
    if (pendingToolUses.length > 0) {
      // Pair with first queued tool_use (FIFO order)
      const toolUse = pendingToolUses.shift();
      const toolResult = data.content;
      createAndAppendAction(toolUse, toolResult);
    }
    return;
  }

  // Check scroll position BEFORE adding content (for smart auto-scroll)
  const wasAtBottom = isAtBottom();

  // When user speaks, add footnotes to previous assistant message and reset turn
  if (type === 'user') {
    addFootnotesToLastAssistant();
    currentTurnActions = [];
    lastAssistantBlock = null;
  }

  if (type === 'assistant') {
    addFootnotesToLastAssistant();
  }

  // Why: knowledge.html renders its history without message ids.
  const partId = String(data.id ?? `local-${assistantParts.size}`);

  if (type === 'assistant' && streamingBlock) {
    streamingBlock.dataset.msgId += ` ${partId}`;
    updateAssistantBlock(streamingBlock, partId, data.content);
    lastAssistantBlock = streamingBlock;
    return streamingBlock;
  }

  const block = document.createElement('div');
  block.className = `event-block event-${type}`;
  if (data.id) block.dataset.msgId = data.id;

  if (type === 'user') {
    // Safe: formatUserContent escapes all user text via escapeHtml()
    block.innerHTML = formatUserContent(data.content);
  } else if (type === 'assistant') {
    streamingBlock = block;
    lastAssistantBlock = block;
    block.dataset.msgId = partId;
    updateAssistantBlock(block, partId, data.content);
    // Why: pas de mermaid ici — le contenu est encore partiel pendant le streaming.
    // Les diagrammes sont rendus une fois le bloc complet (fin de stream, chargement d'historique).
    setTimeout(() => renderOptions(block), 0);
  } else if (type === 'limit') {
    block.innerHTML = `<i class="ri-time-line" aria-hidden="true"></i><div>${escapeHtml(data.content || '')}</div>`;
  } else if (type === 'error') {
    block.innerHTML = escapeHtml(data.content || '');
  } else if (type === 'report') {
    // Report card - parse JSON content
    let reportData = data.content;
    if (typeof reportData === 'string') {
      try {
        reportData = JSON.parse(reportData);
      } catch {}
    }
    // Safe: formatReportCard escapes title via escapeHtml() and validates reportId
    block.innerHTML = formatReportCard(reportData);
  }

  chatOutput.appendChild(block);

  // Keep the loading indicator at the bottom (appendChild moves existing elements)
  const loadingEl = document.getElementById('loadingIndicator');
  if (loadingEl) {
    chatOutput.appendChild(loadingEl);
  }

  // Scan assistant messages for <h2> headings to populate TOC
  if (type === 'assistant') {
    scanHeadingsForToc(block);
  }

  // Only auto-scroll if user was already at bottom (preserves scroll position if reading history)
  if (wasAtBottom) {
    scrollToBottom();
  }

  return block;
}

// =============================================================================
// Format functions
// =============================================================================

/**
 * Detect if content is a report (has YAML front-matter)
 * Returns report info object or null
 */
function detectReport(content) {
  if (!content) return null;

  // Check for YAML front-matter (starts with ---)
  const fmMatch = content.match(/^---\n([\s\S]*?)\n---\n/);
  if (!fmMatch) return null;

  const frontMatter = fmMatch[1];
  const info = { frontMatter: {} };

  // Parse front-matter fields
  const lines = frontMatter.split('\n');
  for (const line of lines) {
    const match = line.match(/^(\w[\w\s]*?):\s*(.+)$/);
    if (match) {
      info.frontMatter[match[1].trim()] = match[2].trim();
    }
  }

  // Try to find report filename (YYYY-MM-*.md pattern)
  const filenameMatch = content.match(/(\d{4}-\d{2}-[\w-]+\.md)/);
  if (filenameMatch) {
    info.filename = filenameMatch[1];
  }

  return info;
}

/**
 * Format a report with special styling and link
 */
function formatReport(content, reportInfo) {
  // Remove YAML front-matter for display
  const bodyContent = content.replace(/^---\n[\s\S]*?\n---\n/, '');

  // Build report header with metadata
  let header = '<div class="report-header">';
  header += '<div class="report-title">';
  header += '<i class="ri-file-text-line"></i> ';
  header += reportInfo.frontMatter['query category'] || 'Rapport';
  header += '</div>';

  if (reportInfo.frontMatter.date) {
    header += `<div class="report-meta"><i class="ri-calendar-line"></i> ${reportInfo.frontMatter.date}</div>`;
  }
  if (reportInfo.frontMatter.website) {
    header += `<div class="report-meta"><i class="ri-global-line"></i> ${reportInfo.frontMatter.website}</div>`;
  }

  // Add link to view full report if filename detected
  if (reportInfo.filename) {
    header += `<a href="/api/reports/${reportInfo.filename}" target="_blank" class="report-link">`;
    header += '<i class="ri-external-link-line"></i> Voir le rapport complet';
    header += '</a>';
  }

  header += '</div>';

  // Format the body content
  const formattedBody = formatAssistantContent(bodyContent);

  return `${header}<div class="report-body">${formattedBody}</div>`;
}

/**
 * Format assistant content using marked.js for proper markdown
 */
function formatAssistantContent(content) {
  if (!content) return '';

  // Use marked.js if available, fallback to simple formatting
  if (typeof marked !== 'undefined') {
    // Configure marked for safe rendering
    marked.setOptions({
      breaks: true, // GFM line breaks
      gfm: true, // GitHub Flavored Markdown
    });

    return marked.parse(content);
  }

  // Fallback: simple markdown-ish
  let html = escapeHtml(content);
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\n/g, '<br>');
  return html;
}

/**
 * Render mermaid diagrams in an element
 */
async function renderMermaid(element) {
  if (typeof mermaid === 'undefined') return;

  const nodes = [];
  for (const block of element.querySelectorAll('pre code.language-mermaid')) {
    const container = document.createElement('div');
    container.className = 'mermaid';
    container.textContent = block.textContent;
    block.parentElement.replaceWith(container);
    nodes.push(container);
  }
  if (!nodes.length) return;

  try {
    await mermaid.run({ nodes });
  } catch (err) {
    console.error('Mermaid rendering failed:', err);
  }
}

/**
 * Render options blocks as clickable buttons
 * Format: ```options\nLabel\nLabel | full request text\n```
 * Text after | is the full prompt (editable by user), defaults to label
 */
function renderOptions(element) {
  const codeBlocks = element.querySelectorAll('pre code.language-options');

  for (const block of codeBlocks) {
    const code = block.textContent.trim();
    const lines = code.split('\n').filter((line) => line.trim());

    // Sanity check: real options blocks are short lists of choices.
    // If the block is too long, it's a malformed code fence — leave it as-is.
    if (lines.length > 6 || lines.length === 0) continue;

    const container = document.createElement('div');
    container.className = 'options-buttons';

    lines.forEach((line, index) => {
      const parts = line.split('|').map((p) => p.trim());
      const label = parts[0];
      const fullPrompt = parts[1] || label;

      const button = document.createElement('button');
      // Last button is primary (recommended action), rest are outline
      const isLast = index === lines.length - 1;
      button.className = isLast ? 'btn btn-primary btn-sm' : 'btn btn-outline-primary btn-sm';
      button.textContent = label;
      button.dataset.prompt = fullPrompt;

      button.addEventListener('click', () => {
        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
          chatInput.value = button.dataset.prompt;
          chatInput.focus();
          // Auto-resize textarea if needed
          chatInput.style.height = 'auto';
          chatInput.style.height = `${chatInput.scrollHeight}px`;
        }
      });

      container.appendChild(button);
    });

    // Replace the code block with buttons
    const preElement = block.parentElement;
    preElement.replaceWith(container);
  }
}

/**
 * Format tool use event - collapsible with tool name on first line
 */
function formatToolUse(content) {
  if (!content) return '';

  const tool = content.tool || 'Unknown';
  const input = content.input || {};

  const inputStr = typeof input === 'object' ? JSON.stringify(input, null, 2) : String(input);
  const lines = inputStr.split('\n');
  const isLong = lines.length > 2;

  // Preview: first 2 lines
  const preview = lines.slice(0, 2).join('\n') + (isLong ? '\n…' : '');

  let html = `<div class="tool-header" onclick="toggleToolContent(this)">`;
  html += `<span class="tool-name">${escapeHtml(tool)}</span>`;
  if (isLong) {
    html += `<span class="tool-toggle"><i class="ri-arrow-down-s-line"></i></span>`;
  }
  html += `</div>`;

  html += `<div class="tool-content tool-preview">${escapeHtml(preview)}</div>`;
  if (isLong) {
    html += `<div class="tool-content tool-full">${escapeHtml(inputStr)}</div>`;
  }

  return html;
}

/**
 * Format tool result event - collapsible with tool name on first line
 */
function formatToolResult(content) {
  if (!content) return '';

  const tool = content.tool || '';
  const output = content.output || '';

  const outputStr = typeof output === 'object' ? JSON.stringify(output, null, 2) : String(output);
  const lines = outputStr.split('\n');
  const isLong = lines.length > 2;

  // Preview: first 2 lines
  const preview = lines.slice(0, 2).join('\n') + (isLong ? '\n…' : '');

  let html = `<div class="tool-header" onclick="toggleToolContent(this)">`;
  if (tool) {
    html += `<span class="tool-name">${escapeHtml(tool)}</span>`;
  }
  if (isLong) {
    html += `<span class="tool-toggle"><i class="ri-arrow-down-s-line"></i></span>`;
  }
  html += `</div>`;

  html += `<div class="tool-content tool-preview">${escapeHtml(preview)}</div>`;
  if (isLong) {
    html += `<div class="tool-content tool-full">${escapeHtml(outputStr)}</div>`;
  }

  return html;
}

/**
 * Toggle tool content visibility
 */
function toggleToolContent(header) {
  const block = header.closest('.event-block');
  if (!block) return;

  block.classList.toggle('tool-expanded');

  // Update icon
  const icon = header.querySelector('.tool-toggle i');
  if (icon) {
    if (block.classList.contains('tool-expanded')) {
      icon.className = 'ri-arrow-up-s-line';
    } else {
      icon.className = 'ri-arrow-down-s-line';
    }
  }
}

/**
 * Format user message content, converting file context blocks to pills
 */
function formatUserContent(content) {
  // Pattern to match file context blocks:
  // [Uploaded file: filename]
  // - Size: ...
  // - Type: ...
  // - Path: ...
  // - Content (...): (optional, with code block)
  // - Note: ... (optional)
  const fileBlockPattern = /\[Uploaded file: ([^\]]+)\]\n(?:- [^\n]+\n)+(?:```[\s\S]*?```\n?)?/g;

  let result = content;
  const matches = content.match(fileBlockPattern);

  if (matches) {
    for (const match of matches) {
      // Extract filename from the match
      const filenameMatch = match.match(/\[Uploaded file: ([^\]]+)\]/);
      const filename = filenameMatch ? filenameMatch[1] : 'Fichier';

      // Extract file size
      const sizeMatch = match.match(/- Size: ([\d,]+) bytes/);
      const size = sizeMatch ? formatFileSize(parseInt(sizeMatch[1].replace(/,/g, ''), 10)) : '';

      // Extract file type
      const typeMatch = match.match(/- Type: ([^\n]+)/);
      const mimeType = typeMatch ? typeMatch[1] : '';

      // Determine icon based on mime type
      let icon = 'ri-file-line';
      if (mimeType.startsWith('image/')) icon = 'ri-image-line';
      else if (mimeType.startsWith('text/') || mimeType.includes('json') || mimeType.includes('xml'))
        icon = 'ri-file-text-line';
      else if (mimeType.includes('pdf')) icon = 'ri-file-pdf-line';
      else if (mimeType.includes('spreadsheet') || mimeType.includes('excel') || mimeType.includes('csv'))
        icon = 'ri-file-excel-line';
      else if (mimeType.includes('word') || mimeType.includes('document')) icon = 'ri-file-word-line';

      // Create pill HTML
      const pill = `<span class="file-context-pill" title="${escapeHtml(mimeType)}"><i class="${icon}"></i> ${escapeHtml(filename)}${size ? ` <span class="file-context-size">(${size})</span>` : ''}</span>`;

      result = result.replace(match, pill);
    }
  }

  // Handle remaining content (the actual user message after ---)
  // Split by --- separator if present
  const parts = result.split(/\n---\n/);
  if (parts.length > 1) {
    // Pills are in first part, user message in second
    const pills = parts[0];
    const userText = parts.slice(1).join('\n---\n').trim();
    if (userText) {
      return `<div class="file-context-pills">${pills}</div><div class="user-text">${formatUserMarkdown(userText)}</div>`;
    } else {
      return `<div class="file-context-pills">${pills}</div>`;
    }
  }

  // If no file blocks found, render as markdown
  if (!matches) {
    return `<div class="user-text">${formatUserMarkdown(content)}</div>`;
  }

  return result;
}

// Why: user content is untrusted. marked auto-escapes text content but passes
// raw HTML through and emits unsanitized link/image hrefs — override those
// three renderer hooks to neutralize <script>/<img>, javascript:/data: hrefs,
// and external image loads.
function formatUserMarkdown(text) {
  if (!text) return '';

  if (typeof marked === 'undefined') {
    return escapeHtml(text).replace(/\n/g, '<br>');
  }

  const renderer = new marked.Renderer();
  renderer.link = function ({ href, title, tokens }) {
    const inner = this.parser.parseInline(tokens);
    if (!isSafeUserUrl(href)) return inner;
    const titleAttr = title ? ` title="${escapeHtml(title)}"` : '';
    return `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer nofollow ugc"${titleAttr}>${inner}</a>`;
  };
  renderer.image = ({ text, title }) => escapeHtml(text || title || '');
  renderer.html = ({ text }) => escapeHtml(text);

  return marked.parse(text, { breaks: true, gfm: true, renderer });
}

/**
 * Format a report card for display in conversation
 */
function formatReportCard(data) {
  const reportId = typeof data.report_id === 'number' ? data.report_id : typeof data.id === 'number' ? data.id : 0;
  const title = data.title || 'Rapport';
  const viewUrl = `/rapports/${reportId}`;

  return `
    <div class="report-card-inline">
      <a href="${viewUrl}" class="report-card-link">
        <i class="ri-file-text-line"></i>
        <span class="report-card-title">${escapeHtml(title)}</span>
        <i class="ri-arrow-right-s-line"></i>
      </a>
    </div>
  `;
}

/**
 * Show error message
 */
function showError(message) {
  appendEvent('error', { content: message });
}
