/**
 * Pure utility functions — no dependencies on other chat modules.
 */

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function autoGrow(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
}

function isAtBottom() {
  const chatOutput = document.getElementById('chatOutput');
  if (!chatOutput) return true;

  // Consider "at bottom" if within 100px of the bottom
  const threshold = 100;
  return chatOutput.scrollHeight - chatOutput.scrollTop - chatOutput.clientHeight < threshold;
}

function scrollToBottom() {
  // Scroll container is .chat-main, not .chat-output
  const chatMain = document.querySelector('.chat-main');
  if (chatMain) {
    chatMain.scrollTop = chatMain.scrollHeight;
  }
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' o';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' Ko';
  return (bytes / (1024 * 1024)).toFixed(1) + ' Mo';
}

// Why: user markdown can produce link hrefs; browsers tolerate whitespace and
// control chars inside scheme prefixes (e.g. "java\tscript:"), so reject any
// control char outright and strip whitespace before the scheme allowlist check.
function isSafeUserUrl(url) {
  if (!url) return false;
  const s = String(url);
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    if (c < 32 || c === 127) return false;
  }
  const cleaned = s.replace(/\s+/g, '').toLowerCase();
  return cleaned.startsWith('http://')
    || cleaned.startsWith('https://')
    || cleaned.startsWith('mailto:')
    || cleaned.startsWith('/')
    || cleaned.startsWith('#');
}

function truncateFilename(name, maxLen = 25) {
  if (name.length <= maxLen) return name;
  const ext = name.includes('.') ? '.' + name.split('.').pop() : '';
  const stem = name.slice(0, name.length - ext.length);
  const truncated = stem.slice(0, maxLen - ext.length - 3) + '...';
  return truncated + ext;
}
