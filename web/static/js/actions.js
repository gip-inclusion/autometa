/**
 * Actions sidebar (pills the server renders, their filter and what opens from them), table of contents, favourites.
 * Depends on: utils.js (escapeHtml), stream.js (conversationHold, currentConversationId)
 */

let actionsFilterMode = localStorage.getItem('actionsFilterMode') || 'data';

// TOC (table of contents) state
let tocEntries = []; // Array of {headingElement, text, element}
let currentSidebarTab = localStorage.getItem('sidebarTab') || 'toc';

// =============================================================================
// Filter
// =============================================================================

/**
 * Show the pills the filter keeps, each named for it: a tool that called APIs is named by their count among the data
 */
function applyActionsFilter() {
  const data = actionsFilterMode === 'data';
  for (const pill of document.querySelectorAll('.action-pill')) {
    pill.classList.toggle('filtered-out', data && !('data' in pill.dataset));
    const summary = pill.querySelector('.action-pill-label > [data-summary]');
    if (!summary) continue;
    const name = pill.querySelector('.action-pill-label > :not([data-summary])');
    const [main, sub] = data ? [summary, name] : [name, summary];
    main.className = 'action-pill-label-main';
    sub.className = 'action-pill-label-sub';
    main.after(sub);
  }
}

/**
 * Put pills the server rendered in the sidebar, each in place of the one of its tool call if there is one, and copy
 * the sidebar to the phone's panel
 */
function showPills(html) {
  const actionsContent = document.getElementById('actionsContent');
  if (!actionsContent) return;
  // Safe: the server escapes what a pill shows of a tool call (web/templates/_action_pill.html)
  const rendered = document.createElement('template');
  rendered.innerHTML = html;
  for (const pill of [...rendered.content.children]) {
    const shown = actionsContent.querySelector(`[data-action-index="${pill.dataset.actionIndex}"]`);
    if (shown) shown.replaceWith(pill);
    else actionsContent.appendChild(pill);
  }
  document
    .getElementById('actionsOffcanvasContent')
    ?.replaceChildren(...[...actionsContent.children].map((pill) => pill.cloneNode(true)));
  applyActionsFilter();
  scrollActionsToBottom();
}

/**
 * Initialize filter toggle listeners
 */
function initActionsFilterToggle() {
  const toggle = document.getElementById('actionsFilterToggle');
  if (!toggle) return;

  // Remove existing listeners by cloning
  const newToggle = toggle.cloneNode(true);
  toggle.replaceWith(newToggle);

  // Sync UI with current filter mode
  newToggle.querySelectorAll('.actions-filter-btn').forEach((b) => {
    b.classList.toggle('active', b.dataset.filter === actionsFilterMode);
  });

  newToggle.addEventListener('click', (e) => {
    const btn = e.target.closest('.actions-filter-btn');
    if (!btn) return;

    const filter = btn.dataset.filter;
    if (filter === actionsFilterMode) return;

    // Update active state
    newToggle.querySelectorAll('.actions-filter-btn').forEach((b) => {
      b.classList.remove('active');
    });
    btn.classList.add('active');

    actionsFilterMode = filter;
    localStorage.setItem('actionsFilterMode', filter);
    applyActionsFilter();
  });
}

/**
 * Switch to detailed filter mode if needed
 */
function switchToDetailedMode() {
  if (actionsFilterMode === 'detailed') return;

  actionsFilterMode = 'detailed';

  // Update toggle UI
  const toggle = document.getElementById('actionsFilterToggle');
  if (toggle) {
    toggle.querySelectorAll('.actions-filter-btn').forEach((b) => {
      b.classList.toggle('active', b.dataset.filter === 'detailed');
    });
  }

  applyActionsFilter();
}

// =============================================================================
// Sidebar tabs (TOC / Actions)
// =============================================================================

/**
 * Initialize sidebar tab toggle (TOC / Actions)
 */
function initSidebarTabToggle() {
  const toggle = document.getElementById('sidebarTabToggle');
  const sidebar = document.getElementById('actionsSidebar');
  if (!toggle || !sidebar) return;

  // Remove existing listeners by cloning
  const newToggle = toggle.cloneNode(true);
  toggle.replaceWith(newToggle);

  // Sync UI with current tab (CSS uses data-active-tab for content visibility)
  syncSidebarTabState();

  newToggle.addEventListener('click', (e) => {
    const btn = e.target.closest('.sidebar-tab-btn');
    if (!btn) return;

    const tab = btn.dataset.tab;
    if (tab === currentSidebarTab) return;

    currentSidebarTab = tab;
    localStorage.setItem('sidebarTab', tab);
    syncSidebarTabState();
  });
}

/**
 * Switch to a specific sidebar tab
 */
function switchSidebarTab(tab) {
  if (tab === currentSidebarTab) return;

  currentSidebarTab = tab;
  localStorage.setItem('sidebarTab', tab);
  syncSidebarTabState();
}

/**
 * Force-sync sidebar tab visibility from localStorage.
 * CSS uses [data-active-tab] on the sidebar as single source of truth for content visibility.
 */
function syncSidebarTabState() {
  const sidebar = document.getElementById('actionsSidebar');
  const toggle = document.getElementById('sidebarTabToggle');

  if (sidebar) sidebar.dataset.activeTab = currentSidebarTab;
  if (toggle) {
    toggle.querySelectorAll('.sidebar-tab-btn').forEach((b) => {
      b.classList.toggle('active', b.dataset.tab === currentSidebarTab);
    });
  }
}

// =============================================================================
// TOC (Table of Contents)
// =============================================================================

/**
 * Add a TOC entry for a section, table or chart of an assistant message
 */
function addTocEntry(target) {
  const tocContent = document.getElementById('tocContent');
  if (!tocContent) return;

  // Remove empty state if present
  const emptyState = tocContent.querySelector('.toc-empty');
  if (emptyState) emptyState.remove();

  const { anchorKind, anchorTitle, anchorLevel, anchorUrl } = target.dataset;
  const figure = {
    table: { icon: 'ri-table-line', name: 'Tableau' },
    chart: { icon: 'ri-bar-chart-2-line', name: 'Graphique' },
  }[anchorKind];
  // Why: a section reads as on the page; a figure has no text of its own to show, so it takes the server's title.
  const text = figure ? anchorTitle || figure.name : target.textContent.trim();
  const entry = document.createElement('div');
  // Why: answers usually start at ##, so levels 1 and 2 share the margin; a figure sits one notch under its section.
  entry.className = `toc-entry toc-level-${Math.min(Number(anchorLevel) || 1, 4)}`;
  entry.innerHTML = `
    ${figure ? `<div class="toc-entry-icon"><i class="${figure.icon}" aria-hidden="true"></i></div>` : ''}
    <div class="toc-entry-content">
      <div class="toc-entry-text">${escapeHtml(text)}</div>
    </div>
  `;

  entry.addEventListener('click', () => {
    if (anchorUrl) history.replaceState(history.state, '', anchorUrl);
    else if (target.id) history.replaceState(history.state, '', `/c/${currentConversationId}#${target.id}`);
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  tocContent.appendChild(entry);
  tocEntries.push({ headingElement: target, text, element: entry });
}

/**
 * Give each <h2> of an assistant block its id, then list the block in the TOC
 */
function scanHeadingsForToc(block) {
  // Why: addresses ending in #<slug> were shared before permalinks existed; every ## keeps that id.
  for (const h2 of block.querySelectorAll('h2')) {
    const text = h2.textContent.trim();
    if (text) h2.id = ensureUniqueId(generateSlug(text));
  }
  // Why: an answer still being written, or one the server slices differently, has no anchors; its ## stand in.
  const anchored = block.querySelectorAll('[data-anchor]');
  for (const target of anchored.length ? anchored : block.querySelectorAll('h2[id]')) addTocEntry(target);
}

/**
 * Generate a URL-friendly slug from text
 */
function generateSlug(text) {
  return (
    text
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .substring(0, 60) || 'section'
  );
}

/**
 * Ensure an element ID is unique in the document
 */
function ensureUniqueId(baseId) {
  if (!document.getElementById(baseId)) return baseId;
  let counter = 2;
  while (document.getElementById(`${baseId}-${counter}`)) {
    counter++;
  }
  return `${baseId}-${counter}`;
}

/**
 * Rebuild the table of contents from every assistant block, after one was re-rendered
 */
function rebuildToc() {
  resetTocState();
  for (const h2 of document.querySelectorAll('#chatOutput .event-assistant h2')) h2.removeAttribute('id');
  for (const block of document.querySelectorAll('#chatOutput .event-assistant')) scanHeadingsForToc(block);
}

/**
 * Reset TOC state for new conversation
 */
function resetTocState() {
  tocEntries = [];

  const tocContent = document.getElementById('tocContent');
  if (tocContent) {
    tocContent.innerHTML = '<div class="toc-empty">Aucune section</div>';
  }
}

// =============================================================================
// Pills: what opens from them
// =============================================================================

/**
 * Open the detail modal with full content
 */
function openActionModal(title, content, isCode) {
  const modal = document.getElementById('actionDetailModal');
  if (!modal) return;

  document.getElementById('actionDetailModalTitle').textContent = title;
  const body = document.getElementById('actionDetailModalBody');
  if (isCode) {
    body.innerHTML = `<pre class="action-modal-pre"><code>${escapeHtml(content)}</code></pre>`;
  } else {
    body.innerHTML = `<div class="action-modal-text">${escapeHtml(content)}</div>`;
  }
  new bootstrap.Modal(modal).show();
}

// Why: pills and references come from the server as HTML, at any time; what they answer to is listened for on the page.
document.addEventListener('click', (e) => {
  const header = e.target.closest('.action-pill-header');
  if (header) return header.parentElement.classList.toggle('expanded');
  const footnote = e.target.closest('.action-footnote');
  if (footnote) return scrollToPillAndExpand(footnote.dataset.actionIndex);

  // A value the pill shows cut short: the server gives it whole
  const button = e.target.closest('.action-expand-btn');
  // Why: a second click while the value is on its way would open it twice.
  if (!button || button.asked) return;
  button.asked = true;
  const { title, whole } = button.dataset;
  const isCode = 'code' in button.dataset;
  // Why: given up when the page leaves the conversation; its answer would open over another page.
  const hold = conversationHold;
  fetch(whole, { signal: hold?.signal })
    .then((response) => (response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`))))
    .then(({ text }) => hold?.signal.aborted || openActionModal(title, text, isCode))
    .catch((error) => {
      if (hold?.signal.aborted) return;
      console.error('Failed to load the whole value:', error);
      const shown = button.closest('.action-kv')?.querySelector('.action-kv-value') ?? button.previousElementSibling;
      const start = shown.textContent.replace(/\.\.\.$/, '');
      openActionModal(title, `${start}\n\n… (la suite n'a pas pu être chargée)`, isCode);
    })
    .finally(() => {
      button.asked = false;
    });
});

for (const [type, highlight] of [
  ['mouseover', true],
  ['mouseout', false],
]) {
  document.addEventListener(type, (e) => {
    const pill = e.target.closest?.('.action-pill');
    if (pill) highlightFootnote(pill.dataset.actionIndex, highlight);
    const footnote = e.target.closest?.('.action-footnote');
    if (footnote) highlightPill(footnote.dataset.actionIndex, highlight);
  });
}

// =============================================================================
// Footnotes & highlighting
// =============================================================================

/**
 * Highlight a pill by index
 */
function highlightPill(idx, highlight) {
  const pills = document.querySelectorAll(`.action-pill[data-action-index="${idx}"]`);
  pills.forEach((pill) => {
    pill.classList.toggle('highlighted', highlight);
  });
}

/**
 * Highlight a footnote by index
 */
function highlightFootnote(idx, highlight) {
  const footnotes = document.querySelectorAll(`.action-footnote[data-action-index="${idx}"]`);
  footnotes.forEach((fn) => {
    fn.classList.toggle('highlighted', highlight);
  });
}

/**
 * Scroll to a pill and expand it
 */
function scrollToPillAndExpand(idx) {
  // Switch to Actions tab first
  switchSidebarTab('actions');

  // Check if pill is filtered out - switch to detailed mode
  const pill = document.querySelector(`#actionsContent .action-pill[data-action-index="${idx}"]`);
  if (pill?.classList.contains('filtered-out')) {
    switchToDetailedMode();
  }

  // On mobile, open offcanvas first
  const offcanvas = document.getElementById('actionsOffcanvas');
  if (offcanvas && window.innerWidth < 992) {
    const bsOffcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvas);
    bsOffcanvas.show();

    // Wait for offcanvas to open, then scroll
    setTimeout(() => {
      const mobilePill = offcanvas.querySelector(`.action-pill[data-action-index="${idx}"]`);
      if (mobilePill) {
        mobilePill.scrollIntoView({ behavior: 'smooth', block: 'center' });
        mobilePill.classList.add('expanded');
      }
    }, 300);
  } else {
    // Desktop: scroll in sidebar
    if (pill) {
      pill.scrollIntoView({ behavior: 'smooth', block: 'center' });
      pill.classList.add('expanded');
    }
  }
}

// =============================================================================
// Misc
// =============================================================================

/**
 * Scroll the actions sidebar tab content to the bottom.
 */
function scrollActionsToBottom() {
  const actionsContent = document.getElementById('actionsContent');
  if (actionsContent) {
    actionsContent.scrollTop = actionsContent.scrollHeight;
  }
}

// Hide public warning banner if previously dismissed - runs on every htmx load
document.body.addEventListener('htmx:afterSettle', () => {
  if (localStorage.getItem('publicWarningDismissed') === 'true') {
    const warning = document.getElementById('publicWarning');
    if (warning) warning.style.display = 'none';
  }
});

function toggleFavorite(btn) {
  const { itemType, itemId } = btn.dataset;
  const isFavorite = btn.classList.contains('is-favorite');
  fetch(`/api/favorites/${itemType}/${itemId}`, { method: isFavorite ? 'DELETE' : 'POST' }).then((response) => {
    if (!response.ok) return;
    btn.classList.toggle('is-favorite', !isFavorite);
    const label = isFavorite ? 'Ajouter aux favoris' : 'Retirer des favoris';
    btn.title = label;
    btn.setAttribute('aria-label', label);
    btn.setAttribute('aria-pressed', String(!isFavorite));
    btn.querySelector('i').className = isFavorite ? 'ri-star-line' : 'ri-star-fill';
  });
}

function removeFavoriteTile(btn) {
  const tile = btn.closest('.accueil-favorite');
  fetch(`/api/favorites/${tile.dataset.itemType}/${tile.dataset.itemId}`, { method: 'DELETE' }).then((response) => {
    if (response.ok) tile.remove();
  });
}

function initFavoritesDnd() {
  const grid = document.getElementById('favoritesGrid');
  // Why: a property, not a data attribute — Back puts back a saved copy of the page's HTML, attributes included.
  if (!grid || grid.dndReady) return;
  grid.dndReady = true;
  let dragged = null;

  grid.addEventListener('dragstart', (event) => {
    dragged = event.target.closest('.accueil-favorite');
    if (dragged) dragged.classList.add('dragging');
  });

  grid.addEventListener('dragover', (event) => {
    event.preventDefault();
    const target = event.target.closest('.accueil-favorite');
    if (!dragged || !target || target === dragged) return;
    const draggedComesFirst = target.compareDocumentPosition(dragged) & Node.DOCUMENT_POSITION_PRECEDING;
    grid.insertBefore(dragged, draggedComesFirst ? target.nextSibling : target);
  });

  grid.addEventListener('dragend', () => {
    if (!dragged) return;
    dragged.classList.remove('dragging');
    dragged = null;
    const items = [...grid.querySelectorAll('.accueil-favorite')].map((tile) => ({
      item_type: tile.dataset.itemType,
      item_id: tile.dataset.itemId,
    }));
    fetch('/api/favorites/order', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items }),
    });
  });
}

document.addEventListener('DOMContentLoaded', initFavoritesDnd);
document.body.addEventListener('htmx:afterSettle', initFavoritesDnd);
