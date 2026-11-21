/**
 * Permalinks: a "copy link" on each finished answer, section, table and chart, and the highlight of a link's target.
 * Depends on: stream.js (currentConversationId), actions.js (rebuildToc)
 */

// Why: a chart is a div.mermaid once drawn, and stays a code block when Mermaid is unavailable.
const PERMALINK_ELEMENTS = {
  section: { selector: 'h1, h2, h3, h4, h5, h6', label: 'cette section' },
  table: { selector: 'table', label: 'ce tableau' },
  chart: { selector: '.mermaid, pre:has(> code.language-mermaid)', label: 'ce graphique' },
};

function permalinkButton(messageId, label, anchor) {
  const url = new URL(`/explorations/${currentConversationId}`, window.location.origin);
  url.searchParams.set('m', messageId);
  if (anchor) url.searchParams.set('a', `${anchor.kind}-${anchor.rank}-${anchor.digest}`);
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'permalink-btn';
  button.dataset.url = url.toString();
  button.title = `Copier le lien vers ${label}`;
  button.setAttribute('aria-label', button.title);
  button.innerHTML = '<i class="ri-link" aria-hidden="true"></i>';
  return button;
}

function attachPermalinks(block, ids, anchors) {
  block.prepend(permalinkButton(ids[0], 'cette réponse'));
  const pairs = [];
  for (const [kind, { selector }] of Object.entries(PERMALINK_ELEMENTS)) {
    const expected = ids.flatMap((id) => anchors[id].filter((a) => a.kind === kind).map((a) => ({ ...a, id })));
    const elements = [...block.querySelectorAll(selector)];
    // Why: the page and the server read Markdown with different parsers; when they disagree, the answer keeps
    // its own link only — no link beats a wrong one.
    if (elements.length !== expected.length) return;
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
      permalink: button.dataset.url,
    });
    if (anchor.kind === 'section') element.append(button);
    else element.before(button);
  }
}

/**
 * Put the links on every finished answer; returns what the address being opened points to, if anything
 */
async function refreshPermalinks() {
  const convId = currentConversationId;
  if (!convId) return null;
  const response = await fetch(`/api/conversations/${convId}/anchors${window.location.search}`);
  if (!response.ok || convId !== currentConversationId) return null;
  const { anchors, target } = await response.json();
  for (const block of document.querySelectorAll('#chatOutput .event-assistant')) {
    for (const button of block.querySelectorAll('.permalink-btn')) button.remove();
    for (const element of block.querySelectorAll('[data-anchor]')) delete element.dataset.anchor;
    const ids = block.dataset.msgId.split(' ');
    // Why: the server lists finished messages only; an answer still being written gets no link.
    if (ids.every((id) => id in anchors)) attachPermalinks(block, ids, anchors);
  }
  rebuildToc();
  return target;
}

function showPermalinkTarget(target) {
  const block = document.querySelector(`#chatOutput [data-msg-id~="${target.message}"]`);
  if (!block) return;
  const named = target.kind && block.querySelector(`[data-anchor="${target.message}-${target.kind}-${target.rank}"]`);
  const element = named || block;
  element.classList.add('permalink-target');
  element.scrollIntoView({ block: 'start' });
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
