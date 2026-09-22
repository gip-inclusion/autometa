const TOKEN_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

function show(id) {
    for (const el of ['invalid-link', 'no-data', 'loading', 'content']) {
        document.getElementById(el).hidden = el !== id;
    }
    document.querySelector('footer').hidden = id !== 'content';
}

// Why: le conteneur Matomo n'est chargé qu'ici, après setCustomUrl. Chargé dans <head>, il
// enverrait l'URL réelle — jeton compris — avant que la page ait pu la remplacer par sa clé.
function track(pageName, title) {
    const dir = location.pathname.replace(/[^/]*$/, '');
    window._paq.push(['HeatmapSessionRecording::disable']);
    window._paq.push(['setCustomUrl', location.origin + dir + pageName + '/']);
    window._paq.push(['setDocumentTitle', title]);
    window._mtm.push({ 'mtm.startTime': new Date().getTime(), event: 'mtm.Start' });
    const container = document.createElement('script');
    container.async = true;
    container.src = 'https://matomo.inclusion.beta.gouv.fr/js/container_TvNd7LvK.js';
    document.head.appendChild(container);
}

function render(data) {
    // TODO : rendre le contenu à partir de `data` (une seule déclinaison)
    document.getElementById('content').textContent = JSON.stringify(data, null, 2);
}

async function init() {
    const token = new URLSearchParams(location.search).get('q') || '';
    if (!TOKEN_RE.test(token)) {
        show('invalid-link');
        track('lien-invalide', document.title);
        return;
    }

    show('loading');
    const response = await fetch('data/' + token + '.json');
    if (!response.ok) {
        show('no-data');
        track('sans-donnees', document.title);
        return;
    }

    const data = await response.json();
    const label = data.metadata?.label || data.metadata?.key || '';
    document.title = label;
    document.getElementById('variant-label').textContent = label;
    document.getElementById('generated-at').textContent = data.metadata?.generated_at || '';
    render(data);
    show('content');
    track(data.metadata?.key || 'sans-cle', label);
}

init().catch(() => {
    show('no-data');
    track('sans-donnees', document.title);
});
