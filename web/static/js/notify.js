/**
 * Notification de fin de réponse : pastille rouge sur le favicon de l'onglet et
 * son court quand un run se termine alors que l'onglet est en arrière-plan
 * (façon Slack). Branché depuis stream.js à chaque fin de run.
 */

const NOTIFY_SOUND = '/static/sounds/notification.wav';

let faviconLink = null;
let baseHref = '';
let badgedHref = '';
let badgePending = false;
let sound = null;

/**
 * Set (or clear) the red dot on the tab favicon.
 */
function setBadge(on) {
  if (!faviconLink) return;
  if (!on) {
    badgePending = false;
    faviconLink.href = baseHref;
    return;
  }
  if (badgedHref) {
    faviconLink.href = badgedHref;
    badgePending = false;
  } else {
    badgePending = true;
  }
}

/**
 * Draw the base icon with a red dot, once, into a reusable data URL.
 */
function buildBadge() {
  const img = new Image();
  img.onload = () => {
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0, 128, 128);
    ctx.beginPath();
    ctx.arc(96, 32, 30, 0, 2 * Math.PI);
    ctx.fillStyle = '#e5484d';
    ctx.fill();
    ctx.lineWidth = 8;
    ctx.strokeStyle = '#ffffff';
    ctx.stroke();
    badgedHref = canvas.toDataURL('image/png');
    if (badgePending) setBadge(true);
  };
  img.src = '/static/favicon.png';
}

function playSound() {
  if (!sound) return;
  sound.currentTime = 0;
  sound.play().catch(() => {});
}

/**
 * Called by stream.js when a run ends. Notifies only when the tab is hidden.
 */
function notifyRunFinished() {
  if (!document.hidden) return;
  setBadge(true);
  playSound();
}

function initTabNotifier() {
  const links = document.querySelectorAll('link[rel="icon"]');
  if (links.length) {
    baseHref = links[0].getAttribute('href') || '';
    links.forEach((l) => {
      l.remove();
    });
  }
  faviconLink = document.createElement('link');
  faviconLink.rel = 'icon';
  faviconLink.id = 'appFavicon';
  faviconLink.href = baseHref;
  document.head.appendChild(faviconLink);

  buildBadge();

  sound = new Audio(NOTIFY_SOUND);
  sound.preload = 'auto';

  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) setBadge(false);
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTabNotifier);
} else {
  initTabNotifier();
}

window.notifyRunFinished = notifyRunFinished;
