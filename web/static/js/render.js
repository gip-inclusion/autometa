/**
 * What the server leaves to the page in the blocks it renders: drawing charts and option buttons. Messages, pills and
 * references arrive as HTML (web/conversation_html.py), on open and from the stream.
 * Depends on: utils.js (scrollToBottom)
 */

/**
 * Render mermaid diagrams in an element
 */
// Why: two runs started in the same millisecond give their charts the same id, and the second comes out broken.
let chartsDrawn = Promise.resolve();

function renderMermaid(element) {
  if (typeof mermaid === 'undefined') {
    // Why: without the library nothing will ever draw them, so their source is all there is to show.
    for (const block of element.querySelectorAll('pre code.language-mermaid')) {
      block.parentElement.classList.add('mermaid-failed');
    }
    return;
  }

  const nodes = [];
  for (const block of element.querySelectorAll('pre code.language-mermaid')) {
    const container = document.createElement('div');
    container.className = 'mermaid';
    container.textContent = block.textContent;
    // Why: the server wrote the chart's permalink on the code block the chart replaces.
    for (const { name, value } of block.parentElement.attributes) {
      if (name.startsWith('data-anchor')) container.setAttribute(name, value);
    }
    block.parentElement.replaceWith(container);
    nodes.push(container);
  }
  if (!nodes.length) return;

  chartsDrawn = chartsDrawn.then(async () => {
    for (const node of nodes) {
      const source = node.textContent;
      try {
        await mermaid.run({ nodes: [node] });
      } catch (err) {
        console.error('Mermaid rendering failed:', err);
        showChartSource(node, source);
      }
    }
  });
  return chartsDrawn;
}

/**
 * Put a chart Mermaid could not draw back as its source: the only time the source is worth reading
 */
function showChartSource(node, source) {
  const failed = document.createElement('pre');
  failed.className = 'mermaid-failed';
  for (const { name, value } of node.attributes) {
    if (name.startsWith('data-anchor')) failed.setAttribute(name, value);
  }
  failed.appendChild(document.createElement('code')).textContent = source;
  node.replaceWith(failed);
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
      // Why: chat.js listens for the click on the page, so buttons in a copy htmx put back still answer.
      button.dataset.prompt = fullPrompt;

      container.appendChild(button);
    });

    // Replace the code block with buttons
    const preElement = block.parentElement;
    preElement.replaceWith(container);
  }
}

/**
 * Draw the charts and options of an answer the server has finished rendering; resolves once its charts are drawn
 */
function drawBlock(block) {
  // Why: an answer still being written may hold half a chart; it comes again once whole.
  if (!block.matches('.event-assistant:not([data-partial])')) return;
  renderOptions(block);
  return renderMermaid(block);
}

/**
 * Show an error of the page's own in the thread
 */
function showError(message) {
  const chatOutput = document.getElementById('chatOutput');
  if (!chatOutput) return;
  const block = document.createElement('div');
  block.className = 'event-block event-error';
  block.textContent = message;
  chatOutput.appendChild(block);
  // Keep the loading indicator at the bottom (appendChild moves existing elements)
  const loading = document.getElementById('loadingIndicator');
  if (loading) chatOutput.appendChild(loading);
  scrollToBottom();
}
