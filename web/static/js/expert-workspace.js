/**
 * Expert workspace: spec panel, conversation selector.
 * Depends on: stream.js (currentConversationId, startStream, loadConversation)
 *             render.js (appendEvent)
 *             utils.js
 */

let _expertConfig = null;
let _specPollTimer = null;
let _activeArtifact = 'spec';

// =============================================================================
// Init
// =============================================================================

function initExpertWorkspace(config) {
  _expertConfig = config;
  initSpecPanel();
  initConvSelector();
}

// =============================================================================
// Spec panel
// =============================================================================

function initSpecPanel() {
  // Clear any previous polling timer (prevents accumulation on htmx navigation)
  if (_specPollTimer) {
    clearInterval(_specPollTimer);
    _specPollTimer = null;
  }

  // Tab switching
  const tabs = document.querySelectorAll('.spec-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      _activeArtifact = tab.dataset.artifact;
      loadSpecContent();
    });
  });

  // Panel toggle (collapse/expand)
  const toggle = document.getElementById('specPanelToggle');
  const panel = document.getElementById('specPanel');
  if (toggle && panel) {
    toggle.addEventListener('click', () => {
      panel.classList.toggle('collapsed');
      const icon = toggle.querySelector('i');
      if (panel.classList.contains('collapsed')) {
        icon.className = 'ri-arrow-right-s-line';
        toggle.title = 'Afficher';
      } else {
        icon.className = 'ri-arrow-left-s-line';
        toggle.title = 'Masquer';
      }
    });
  }

  // Initial load
  loadSpecContent();

  // Poll for updates every 10 seconds
  _specPollTimer = setInterval(loadSpecContent, 10000);
}

async function loadSpecContent() {
  if (!_expertConfig) return;

  const container = document.getElementById('specContent');
  if (!container) return;

  try {
    const res = await fetch(`/api/expert/projects/${_expertConfig.projectId}/spec-files`);
    if (!res.ok) return;

    const data = await res.json();
    const content = data[_activeArtifact];

    if (content && content.trim()) {
      if (typeof marked !== 'undefined') {
        container.innerHTML = marked.parse(content);
      } else {
        container.textContent = content;
      }
    } else {
      const labels = {
        spec: 'specification',
        plan: 'plan technique',
        tasks: 'liste de taches',
        checklist: 'verification qualite',
      };
      container.innerHTML = `
        <div class="spec-empty">
          <i class="ri-file-text-line"></i>
          <p>Pas encore de ${labels[_activeArtifact] || 'contenu'}.</p>
          <p class="small">L'agent le creera pendant la conversation.</p>
        </div>
      `;
    }
  } catch (err) {
    console.warn('Failed to load spec content:', err);
  }
}

// =============================================================================
// Conversation selector
// =============================================================================

function initConvSelector() {
  const selector = document.getElementById('convSelector');
  const newConvBtn = document.getElementById('newConvBtn');

  if (selector) {
    selector.addEventListener('change', () => {
      const convId = selector.value;
      if (convId && _expertConfig) {
        window.location.href = `/expert/${_expertConfig.projectSlug}/${convId}`;
      }
    });
  }

  if (newConvBtn && _expertConfig) {
    newConvBtn.addEventListener('click', async () => {
      try {
        const res = await fetch(`/api/expert/projects/${_expertConfig.projectId}/conversations`, {
          method: 'POST',
        });
        if (res.ok) {
          const data = await res.json();
          window.location.href = data.redirect;
        }
      } catch (err) {
        console.error('Failed to create conversation:', err);
      }
    });
  }
}

// =============================================================================
// Cleanup
// =============================================================================

// Stop polling when navigating away
window.addEventListener('beforeunload', () => {
  if (_specPollTimer) {
    clearInterval(_specPollTimer);
    _specPollTimer = null;
  }
});
