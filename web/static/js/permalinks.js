/**
 * Permalinks: a "copy link" on each finished answer, section, table and chart, and the highlight of a link's target.
 * Depends on: stream.js (currentConversationId), actions.js (rebuildToc), chat.js (parseExplorationPath)
 */

function firstLetters(text) {
  return text.replace(/[^\p{L}\p{N}]/gu, '').slice(0, 40);
}

// Why: a chart is a div.mermaid once drawn, and stays a code block when Mermaid is unavailable. Each element yields
// the witness the server sent for its anchor, so that a pairing is checked, not assumed.
const PERMALINK_ELEMENTS = {
  section: {
    selector: 'h1, h2, h3, h4, h5, h6',
    label: 'cette section',
    witness: (heading) => firstLetters(heading.textContent),
  },
  table: {
    selector: 'table',
    label: 'ce tableau',
    witness: (table) => `${table.rows[0]?.cells.length ?? 0}x${table.tBodies[0]?.rows.length ?? 0}`,
  },
  chart: {
    selector: '.mermaid, pre:has(> code.language-mermaid)',
    label: 'ce graphique',
    witness: (chart) => firstLetters(chart.dataset.source ?? chart.textContent),
  },
};

function permalinkButton(messageId, label, anchor) {
  const element = anchor ? `/${anchor.kind}-${anchor.rank}-${anchor.digest}` : '';
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'permalink-btn';
  button.dataset.url = `${window.location.origin}/explorations/${currentConversationId}/${messageId}${element}`;
  button.title = `Copier le lien vers ${label}`;
  button.setAttribute('aria-label', button.title);
  button.innerHTML = '<i class="ri-link" aria-hidden="true"></i>';
  return button;
}

function attachPermalinks(block, ids, anchors) {
  block.prepend(permalinkButton(ids[0], 'cette réponse'));
  const pairs = [];
  for (const [kind, { selector, witness }] of Object.entries(PERMALINK_ELEMENTS)) {
    const expected = ids.flatMap((id) => anchors[id].filter((a) => a.kind === kind).map((a) => ({ ...a, id })));
    const elements = [...block.querySelectorAll(selector)];
    // Why: the page and the server read Markdown with different parsers; when they disagree on any element, the
    // answer keeps its own link only — no link beats a wrong one.
    if (elements.length !== expected.length) return;
    if (elements.some((element, i) => witness(element) !== expected[i].witness)) return;
    elements.forEach((element, i) => {
      pairs.push([element, expected[i]]);
    });
  }
  for (const [element, anchor] of pairs) {
    const button = permalinkButton(anchor.id, PERMALINK_ELEMENTS[anchor.kind].label, anchor);
    Object.assign(element.dataset, {
      anchor: `${anchor.id}-${anchor.kind}-${anchor.rank}`,
      anchorKind: anchor.kind,
      anchorTitle: anchor.title,
      anchorLevel: anchor.level,
      anchorUrl: button.dataset.url,
    });
    if (anchor.kind === 'section') {
      element.append(button);
      continue;
    }
    // Why: a figure's link lies over its corner, out of the flow, so the figure keeps its place and its width.
    const figure = document.createElement('div');
    figure.className = 'permalink-figure';
    element.replaceWith(figure);
    figure.append(element, button);
  }
}

/**
 * Put the links on every finished answer; returns what the address being opened points to, if anything
 */
async function refreshPermalinks() {
  const convId = currentConversationId;
  if (!convId) return null;
  const { message, anchor } = parseExplorationPath(window.location.pathname) ?? {};
  const url = new URL(`/api/conversations/${convId}/anchors`, window.location.origin);
  if (message) url.searchParams.set('m', message);
  if (anchor) url.searchParams.set('a', anchor);
  let body = null;
  try {
    const response = await fetch(url);
    if (response.ok) body = await response.json();
  } catch (error) {
    console.error('Failed to load permalinks:', error);
  }
  if (!body || convId !== currentConversationId) return null;
  for (const block of document.querySelectorAll('#chatOutput .event-assistant')) {
    for (const button of block.querySelectorAll('.permalink-btn')) button.remove();
    for (const figure of block.querySelectorAll('.permalink-figure')) figure.replaceWith(...figure.childNodes);
    for (const element of block.querySelectorAll('[data-anchor]')) {
      for (const key of Object.keys(element.dataset)) if (key.startsWith('anchor')) delete element.dataset[key];
    }
    const ids = block.dataset.msgId.split(' ');
    // Why: the server lists finished messages only; an answer still being written gets no link.
    if (ids.every((id) => id in body.anchors)) attachPermalinks(block, ids, body.anchors);
  }
  rebuildToc();
  return body.target;
}

/**
 * Outline and scroll to what a permalink points to; false when it is not displayed
 */
function showPermalinkTarget(target) {
  const block = document.querySelector(`#chatOutput [data-msg-id~="${target.message}"]`);
  const named = target.kind && block?.querySelector(`[data-anchor="${target.message}-${target.kind}-${target.rank}"]`);
  const element = named || block;
  // Why: the minimal view hides the answers that are not final; scrolling to one would land nowhere.
  if (!element?.checkVisibility()) return false;
  element.classList.add('permalink-target');
  element.scrollIntoView({ block: 'start' });
  return true;
}

document.addEventListener('click', async (e) => {
  const button = e.target.closest('.permalink-btn');
  if (!button) return;
  try {
    await navigator.clipboard.writeText(button.dataset.url);
  } catch {
    return;
  }
  const icon = button.querySelector('i');
  icon.className = 'ri-check-line';
  setTimeout(() => {
    icon.className = 'ri-link';
  }, 1200);
});
