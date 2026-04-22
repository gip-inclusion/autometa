async function loadData() {
    const response = await fetch('data.json');
    return response.json();
}

async function init() {
    const data = await loadData();

    const generatedAt = data.metadata?.generated_at;
    if (generatedAt) {
        document.getElementById('generated-at').textContent = generatedAt;
    }

    // TODO : rendre le contenu à partir de `data`
    document.getElementById('content').textContent = JSON.stringify(data, null, 2);
}

init();
