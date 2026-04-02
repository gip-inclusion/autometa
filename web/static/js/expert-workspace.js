/**
 * Expert workspace: spec panel, deploy bar, conversation selector.
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
  initDeployBar();
  initConvSelector();
}

// =============================================================================
// Spec panel
// =============================================================================

function initSpecPanel() {
  if (_specPollTimer) {
    clearInterval(_specPollTimer);
    _specPollTimer = null;
  }

  const tabs = document.querySelectorAll('.spec-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      _activeArtifact = tab.dataset.artifact;
      loadSpecContent();
    });
  });

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

  loadSpecContent();
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
// Deploy bar
// =============================================================================

function initDeployBar() {
  const refreshBtn = document.getElementById('deployRefreshBtn');
  const deployStagingBtn = document.getElementById('deployStagingBtn');

  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => refreshDeployStatus());
  }
  if (deployStagingBtn) {
    deployStagingBtn.addEventListener('click', () => deployEnv('staging', deployStagingBtn));
  }

  const stagingRestart = document.getElementById('stagingRestartInline');
  if (stagingRestart) {
    stagingRestart.addEventListener('click', () => restartEnv('staging', stagingRestart));
  }

  const stagingDot = document.getElementById('stagingDot');
  if (stagingDot && _expertConfig) {
    stagingDot.addEventListener('click', () => {
      window.open(`/expert/${_expertConfig.projectSlug}/preview/staging/`, '_blank');
    });
  }

  refreshDeployStatus();
  setInterval(refreshDeployStatus, 15000);
}

async function refreshDeployStatus() {
  if (!_expertConfig) return;

  try {
    const res = await fetch(`/api/expert/projects/${_expertConfig.projectId}/deploy-status`);
    if (!res.ok) return;

    const data = await res.json();
    updateDeployDot('stagingDot', 'stagingLink', data.staging);
  } catch (err) {
    console.warn('Failed to refresh deploy status:', err);
  }
}

function updateDeployDot(dotId, linkId, envData) {
  const dot = document.getElementById(dotId);
  const link = document.getElementById(linkId);
  if (!dot) return;

  const env = dotId.replace('Dot', '');
  const restartBtn = document.getElementById(env + 'RestartInline');

  dot.className = 'deploy-dot';

  const st = envData?.status || '';
  if (!envData || st === 'not_deployed') {
    dot.classList.add('deploy-dot-unknown');
  } else if (st === 'running' || st.startsWith('running:')) {
    dot.classList.add('deploy-dot-running');
  } else if (st === 'deploying' || st === 'starting') {
    dot.classList.add('deploy-dot-deploying');
  } else if (st === 'stopped' || st === 'exited') {
    dot.classList.add('deploy-dot-stopped');
  } else if (st === 'error' || st === 'degraded' || st.includes('unhealthy')) {
    dot.classList.add('deploy-dot-error');
  } else {
    dot.classList.add('deploy-dot-unknown');
  }

  if (link && envData && envData.deploy_url) {
    link.href = envData.deploy_url;
    link.style.display = '';
  } else if (link) {
    link.style.display = 'none';
  }

  const deployed = envData && st !== 'not_deployed';
  if (restartBtn) {
    restartBtn.style.display = (deployed && st !== 'running' && !st.startsWith('running:')) ? '' : 'none';
  }
}

async function deployEnv(env, btn) {
  if (!_expertConfig) return;

  const originalHtml = btn?.innerHTML;
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="ri-loader-4-line ri-spin"></i>';
  }

  const endpoint = env === 'production'
    ? `/api/expert/projects/${_expertConfig.projectId}/deploy`
    : `/api/expert/projects/${_expertConfig.projectId}/deploy-staging`;

  try {
    const res = await fetch(endpoint, { method: 'POST' });
    const data = await res.json();

    if (!res.ok) {
      alert('Erreur de deploiement : ' + (data.error || 'Erreur inconnue'));
    }

    for (let i = 0; i < 3; i++) {
      await new Promise(r => setTimeout(r, 3000));
      await refreshDeployStatus();
    }
  } catch (err) {
    alert('Erreur de connexion : ' + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

async function restartEnv(env, btn) {
  if (!_expertConfig) return;

  const originalHtml = btn?.innerHTML;
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="ri-loader-4-line ri-spin"></i>';
  }

  try {
    const res = await fetch(`/api/expert/projects/${_expertConfig.projectId}/restart/${env}`, { method: 'POST' });
    const data = await res.json();

    if (!res.ok || data.status !== 'running') {
      alert(data.error || 'Restart echoue');
    }

    await new Promise(r => setTimeout(r, 2000));
    await refreshDeployStatus();
  } catch (err) {
    alert('Erreur : ' + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
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

window.addEventListener('beforeunload', () => {
  if (_specPollTimer) {
    clearInterval(_specPollTimer);
    _specPollTimer = null;
  }
});
