/**
 * Permalinks: the "copy link" the server writes on each finished answer, section, table and chart, and the highlight
 * of a link's target.
 */

/**
 * What the address being opened points to: an element of a finished answer, the answer itself when the element is not
 * on it, null when the message is none of the conversation's finished answers
 */
function permalinkTarget(message, anchor) {
  const block = document.querySelector(`#chatOutput > .event-assistant[data-msg-id~="${message}"]`);
  if (!block) return null;
  const [, kind, rank, digest] = /^(section|table|chart)-(\d{1,6})-([0-9a-f]{6})$/.exec(anchor ?? '') ?? [];
  if (!kind) return block;
  // Why: an element moved by a later edit keeps its text: the same digest at another rank of its message still names it.
  const same = [...block.querySelectorAll(`[data-anchor^="${message}-${kind}-"][data-anchor-url$="-${digest}"]`)];
  return same.find((element) => element.dataset.anchor === `${message}-${kind}-${Number(rank)}`) ?? same[0] ?? block;
}

/**
 * Outline and scroll to what a permalink points to; false when it is not displayed
 */
function showPermalinkTarget(element) {
  // Why: the minimal view hides the answers that are not final; scrolling to one would land nowhere. An element not
  // displayed has no boxes, in every browser (checkVisibility is too recent for Safari before 17.4).
  if (!element.getClientRects().length) return false;
  element.classList.add('permalink-target');
  element.scrollIntoView({ block: 'start' });
  return true;
}

function headingLevel(element) {
  return Number(/^H([1-6])$/.exec(element.tagName)?.[1] ?? 7);
}

let outlinedSection = [];

/**
 * The answer that follows a block in its turn, null when the turn says nothing more
 */
function nextAnswer(block) {
  let next = block.nextElementSibling;
  while (next && !next.matches('.event-assistant, .event-user')) next = next.nextElementSibling;
  return next?.matches('.event-assistant') ? next : null;
}

/**
 * Outline a heading's section as the server cuts it: to the next heading of its level or above, through the answers
 * that follow in its turn when none ends it before; null removes the outline
 */
function outlineSection(heading) {
  for (const outlined of outlinedSection) outlined.classList.remove('permalink-section-outline');
  outlinedSection = [];
  if (!heading) return;
  const level = headingLevel(heading);
  const inside = (element) => element && !element.matches('.action-footnotes') && headingLevel(element) > level;
  let block = heading.closest('.event-block');
  let first = heading;
  while (first) {
    let last = first;
    while (inside(last.nextElementSibling)) last = last.nextElementSibling;
    const height = last.getBoundingClientRect().bottom - first.getBoundingClientRect().top;
    first.style.setProperty('--permalink-section-height', `${height}px`);
    first.classList.add('permalink-section-outline');
    outlinedSection.push(first);
    // Why: a heading ended the section in this answer; otherwise it goes on where the next answer starts.
    if (last.nextElementSibling && !last.nextElementSibling.matches('.action-footnotes')) return;
    first = null;
    while (!first) {
      block = nextAnswer(block);
      if (!block) return;
      const body = block.querySelector(':scope > .report-body') ?? block;
      first = [...body.children].find((child) => !child.matches('.permalink-btn, .action-footnotes'));
      if (first && !inside(first)) return;
    }
  }
}

// Why: CSS outlines the answer and the figures under their links, a section needs its range measured. A tap outlines
// nothing that could stay, and a link focused by a click outlines only under the pointer.
function followSectionLink(e) {
  const heading = e.target.closest?.('[data-anchor-kind="section"] > .permalink-btn')?.parentElement;
  if (!heading || e.pointerType === 'touch' || (e.type === 'focusin' && !e.target.matches(':focus-visible'))) return;
  outlineSection(e.type === 'pointerover' || e.type === 'focusin' ? heading : null);
}

for (const type of ['pointerover', 'pointerout', 'focusin', 'focusout']) {
  document.addEventListener(type, followSectionLink);
}

document.addEventListener('click', async (e) => {
  const button = e.target.closest('.permalink-btn');
  if (!button) return;
  try {
    await navigator.clipboard.writeText(new URL(button.dataset.url, window.location.origin).href);
  } catch {
    return;
  }
  const icon = button.querySelector('i');
  icon.className = 'ri-check-line';
  setTimeout(() => {
    icon.className = 'ri-link';
  }, 1200);
});
