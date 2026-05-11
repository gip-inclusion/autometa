# Tableaux de bord

Règles pour créer des tableaux de bord (TDB) frontend dans `/data/interactive/`.

« Tableau de bord » est le terme canonique. « Dashboard » est un synonyme acceptable. « Application interactive » est l'ancien nom — à ne plus utiliser.

Les TDB sont privés par défaut (accessibles aux utilisateurs d'Autometa). Certains peuvent, optionnellement, être rendus publics (cf. spec V1).

## Modèle de données

L'inventaire des TDB vit dans la table `dashboards` en base. C'est la **source de vérité** : un TDB n'apparaît dans la liste, la sidebar, la home, que s'il a une ligne en DB. Le dossier `data/interactive/{slug}/` reste l'endroit où vit le **code** du TDB ; il est synchronisé vers S3 par `web/sync_to_s3.py`.

Flags portés par la ligne `dashboards` :

- `is_archived` — un TDB archivé est invisible des listes par défaut.
- `has_cron` — `cron.py` du TDB doit être exécuté périodiquement.
- `has_api_access` — appelle `/api/query` en live (rend le TDB **non publiable**).
- `has_persistence` — écrit dans le datalake via `/api/query` (idem, **non publiable**).

## Création et modification : passer par les skills

Pour créer un nouveau TDB ou modifier un TDB existant, **toujours** utiliser les skills dédiés. Pas d'écriture directe sur `data/interactive/` ni d'INSERT manuel en DB côté agent.

### `create_dashboard` (création)

Invoquer dès que l'utilisateur demande un nouveau TDB. Le skill copie le template, génère `APP.md`, insère la ligne `dashboards`, et retourne le chemin créé.

```bash
.venv/bin/python skills/create_dashboard/scripts/create_dashboard.py \
    --slug mon-tdb \
    --title "Mon tableau de bord" \
    --description "Description courte" \
    --website emplois \
    --tags trafic,candidats \
    --has-cron
```

### `update_dashboard` (modification)

**Point d'entrée canonique** dès qu'un utilisateur exprime le souhait de modifier un TDB existant. Garantit que c'est le bon slug, met à jour DB + `APP.md`, et retourne l'`originating_user_email` (parfois différent) et le chemin des conventions à respecter pour la suite.

```bash
.venv/bin/python skills/update_dashboard/scripts/update_dashboard.py \
    --slug mon-tdb \
    --title "Nouveau titre" \
    --add-tags trafic --remove-tags ancien-tag \
    --has-api-access true
```

Les deux skills lisent `AUTOMETA_CONVERSATION_ID` et `AUTOMETA_USER_EMAIL` injectés automatiquement dans l'environnement par le runtime agent.

## Stack

- **Vanilla JS** — pas de React, Vue ou autre framework.
- **HTML sémantique** — utiliser les bons éléments (`<nav>`, `<main>`, `<article>`, `<table>`…).
- **CSS** — custom properties, dépendances minimales. Pas de Tailwind.
- **Graphiques** — D3.js ou Observable Plot pour les visualisations complexes, Chart.js pour les plus simples.

## Structure de fichiers

Chaque dashboard vit dans son propre dossier :

```
data/interactive/
└── mon-dashboard/
    ├── APP.md              # OBLIGATOIRE : métadonnées (voir ci-dessous)
    ├── index.html          # Point d'entrée
    ├── style.css           # Styles
    ├── app.js              # Logique applicative
    ├── data.json           # Données statiques (si besoin)
    └── cron.py             # Script de rafraîchissement des données (voir ci-dessous)
```

Ne pas créer de HTML auto-suffisant (CSS et JS inline dans `index.html`) : ce n'est pas découvrable. La structure ci-dessus **doit** être respectée : CSS et JS vivent dans leurs fichiers.

## Point de départ : copier le template

Tout nouveau dashboard part du gabarit dans `docs/dashboard-template/` :

```bash
cp -r docs/dashboard-template data/interactive/mon-dashboard
```

Le template fournit :
- `APP.md` — métadonnées de l'application à compléter
- `index.html` — page minimale à enrichir, mention `generated-at` à compléter sur le pied de page
- `style.css` — police Marianne, palette DSFR, styles de base
- `app.js` — chargement de `data.json` et affichage de la date de fraîcheur
- `cron.py` — stub à remplir avec les appels `lib.query`

Ensuite : compléter `APP.md`, écrire la logique dans `app.js`, remplir (si besoin) `cron.py`.

Si le dashboard n'utilise pas de données pré-calculées (requêtes live via `/api/query` uniquement, ou dashboard qui n'a pas besoin d'être rafraîchi), supprimer `cron.py` et adapter les valeurs `cron` et `has_api_access` dans `APP.md`.

## APP.md

Chaque TDB **doit** avoir un fichier `APP.md` avec front-matter YAML. C'est conservé en parallèle de la DB pour que le dossier `data/interactive/{slug}/` reste lisible seul, et parce que `web/cron.py` y lit encore `schedule`, `timeout`, `enabled`.

```markdown
---
title: Mon Dashboard
description: Description courte affichée sur la carte
updated: 2026-04-22
website: emplois
category: Analyse de trafic
tags: appli, trafic, analyse
cron: true
has_api_access: false
authors: jean@example.com, marie@example.com
conversation_id: abc-123-def
---

## À propos

Documentation optionnelle : usage, régénération des données, etc.
```

**Champ obligatoire :**
- `title` — nom affiché dans la liste des dashboards

**Champs optionnels :**
- `description` — affichée sous le titre dans la carte
- `updated` — date au format `YYYY-MM-DD` (affichée en pied de carte)
- `website` — site associé (voir [Tags valides](#tags-valides))
- `category` — catégorie de filtrage
- `tags` — liste séparée par virgules ou `[tag1, tag2]` (voir [Tags valides](#tags-valides))
- `authors` — emails séparés par virgules
- `conversation_id` — lien vers la conversation d'origine
- `cron` — `true` / `false` pour activer ou désactiver le rafraîchissement programmé (voir [Mode par défaut](#mode-par-défaut--cronpy--datajson))
- `has_api_access` — `true` si le dashboard appelle `/api/query` en live (voir [Modes non publiables](#modes-non-publiables))
- `has_persistence` — `true` si le dashboard lit ou écrit dans le datalake (voir [Persistance en datalake](#persistance-en-datalake))

`has_api_access` et `has_persistence` marquent le dashboard comme non publiable et doivent être déclarés dès qu'un de ces modes est utilisé.

Un dashboard sans `APP.md` valide n'apparaît pas dans la liste.

## Accès aux données

### Pied de page « dernière mise à jour »

Toujours afficher la date de fraîcheur des données en pied de page. Avec `cron.py`, lire `metadata.generated_at` depuis `data.json` (voir ci-dessous). Sans cron, écrire une date en dur correspondant à la dernière régénération manuelle.

```html
<footer>
    <p>Données mises à jour le <span id="generated-at">…</span></p>
</footer>
```

```javascript
const data = await fetch('data.json').then(r => r.json());
const generatedAt = data.metadata?.generated_at;
if (generatedAt) {
    document.getElementById('generated-at').textContent = generatedAt;
}
```

### Mode par défaut : `cron.py` → `data.json`

Sauf cas particulier, la donnée doit être pré-calculée et vivre dans `data.json`. Le frontend lit simplement le fichier :

```javascript
async function loadData() {
    const response = await fetch('data.json');
    return response.json();
}
```

Un script `cron.py` dans le dossier du dashboard refresh `data.json` automatiquement. Ce mode est le seul qui permet de rendre public le dashboard (pas de session authentifiée requise).

#### Installation

```
data/interactive/mon-dashboard/
├── APP.md
├── index.html
├── ...
├── cron.py      ← script de rafraîchissement
└── data.json    ← écrit par cron.py
```

Le script tourne comme un processus Python standard avec `PYTHONPATH` pointé sur la racine du projet. Il peut importer `lib.query` pour appeler Matomo / Metabase. Son working directory est le dossier du dashboard, donc `open('data.json', 'w')` écrit au bon endroit.

En production, `data.json` est synchronisé vers S3 — les fichiers écrits par `cron.py` survivent aux redéploiements.

#### Convention `data.json`

`cron.py` **doit** inclure un champ `metadata.generated_at` (date ISO `YYYY-MM-DD`) :

```json
{
  "metadata": {
    "generated_at": "2026-02-12",
    "source": "Matomo API - VisitsSummary.get"
  },
  "2025": { ... }
}
```

#### Activation

`cron: true` / `cron: false` dans le front-matter `APP.md`. Par défaut `true` quand `cron.py` existe. Bascule disponible depuis l'UI `/cron`.

```yaml
---
title: Mon Dashboard
cron: true
---
```

#### Lancement

```bash
python -m web.cron              # tous les cron activés
python -m web.cron --app slug   # un seul dashboard
python -m web.cron --list       # lister les cron découverts
python -m web.cron --dry-run    # montrer sans exécuter
```

Sur la VM actuelle, entrée crontab système :
```
0 6 * * * cd /path/to/autometa && .venv/bin/python -m web.cron
```

#### Contraintes

- Timeout de 5 minutes par script
- stdout / stderr capturés et stockés en base (50 Ko max)
- Exit code 0 = succès, non nul = échec
- Les fichiers `.py` ne sont **pas servis** via `/interactive/` (404)

#### UI

`/cron` liste tous les dashboards éligibles, leur dernier statut, et permet de déclencher ou toggler manuellement.

### Modes non publiables

Les deux modes qui suivent — requêtes live via `/api/query` et persistance en datalake — dépendent de l'endpoint `/api/query`, protégé par oauth2-proxy. **Un dashboard qui les utilise ne peut pas être publié** : il ne fonctionne que derrière une session authentifiée.

**Ne pas adopter ces modes sans avoir demandé confirmation explicite à l'utilisateur.** Par défaut, pré-calculer les données via `cron.py`.

#### Requêtes live via `/api/query`

À utiliser uniquement si `cron.py` n'est pas envisageable (temps réel strict, navigation aléatoire dans un gros jeu de données). Déclarer `has_api_access: true` dans `APP.md`.

```javascript
async function query(params) {
    const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
    });
    return response.json();
}
```

**Matomo :**

```javascript
const result = await query({
    source: 'matomo',
    instance: 'inclusion',
    method: 'VisitsSummary.get',
    conversation_id: 'mon-dashboard-session-123',  // optionnel, pour audit
    params: {
        idSite: 117,
        period: 'month',
        date: '2025-12-01'
    }
});

if (result.success) {
    console.log(result.data);  // { nb_visits: 405574, ... }
} else {
    console.error(result.error);
}
```

**Metabase :**

```javascript
// SQL
const result = await query({
    source: 'metabase',
    instance: 'stats',       // ou 'datalake'
    database_id: 2,
    sql: 'SELECT * FROM candidats LIMIT 10'
});

// Carte sauvegardée
const result = await query({
    source: 'metabase',
    instance: 'stats',
    card_id: 123
});

// Format de réponse
{
    success: true,
    data: {
        columns: ['id', 'name', ...],
        rows: [[1, 'Alice'], [2, 'Bob']],
        row_count: 2
    },
    execution_time_ms: 234
}
```

**Instances disponibles :** voir `config/sources.yaml`. Les instances Metabase et Matomo y sont listées.

#### Persistance en datalake

Pour qu'un dashboard **lise et écrive des données persistantes** (tracking, assignations, notes, état), passer par PostgreSQL datalake via le même endpoint `/api/query`. Déclarer `has_persistence: true` dans `APP.md`.

**Pourquoi pas de routes FastAPI ?** `web/` est baked dans l'image Docker et pas bind-mounté. Tout fichier créé ou modifié sous `/app/web/` atterrit dans le layer overlay du conteneur et disparaît au prochain restart. Ne jamais créer de routes, routers ou modules Python FastAPI depuis le conteneur.

**Architecture :**

```
Frontend (JS)  ──POST /api/query──▶  FastAPI /api/query  ──▶  Metabase API  ──▶  Datalake PostgreSQL
                                      (existant)              (native query)     (read + write)
```

L'endpoint expose du SQL brut via la native query Metabase. L'utilisateur datalake a les droits en écriture : INSERT, UPDATE, DELETE, CREATE TABLE fonctionnent.

**Schéma `matometa` :** toutes les tables Autometa vivent dans un schéma `matometa` dédié, à l'écart des tables principales dans `public`. Le schéma existe déjà.

**1. Créer la table** (côté agent, script Python) :

```python
from lib.query import execute_metabase_query, CallerType

# DDL s'exécute mais Metabase renvoie une erreur de parse (pas de ResultSet).
# Comportement normal — ignorer, la table EST créée.
execute_metabase_query(
    instance="datalake",
    caller=CallerType.AGENT,
    sql="""
        CREATE TABLE IF NOT EXISTS matometa.myapp_tracking (
            id SERIAL PRIMARY KEY,
            item_id TEXT NOT NULL,
            assigned_to TEXT,
            status TEXT DEFAULT 'pending',
            note TEXT,
            updated_by TEXT,
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(item_id)
        )
    """,
    database_id=2,
)
```

**2. Lecture depuis le frontend** :

```javascript
async function loadTracking() {
    const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            source: 'metabase',
            instance: 'datalake',
            database_id: 2,
            sql: 'SELECT * FROM matometa.myapp_tracking ORDER BY updated_at DESC'
        })
    });
    const result = await response.json();
    if (result.success) {
        return result.data;
    }
    throw new Error(result.error);
}
```

**3. Écriture depuis le frontend** :

```javascript
async function saveTracking(itemId, assignedTo, status, note, userName) {
    const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            source: 'metabase',
            instance: 'datalake',
            database_id: 2,
            sql: `INSERT INTO matometa.myapp_tracking (item_id, assigned_to, status, note, updated_by)
                  VALUES ('${itemId}', '${assignedTo}', '${status}', '${note}', '${userName}')
                  ON CONFLICT (item_id) DO UPDATE
                  SET assigned_to = EXCLUDED.assigned_to,
                      status = EXCLUDED.status,
                      note = EXCLUDED.note,
                      updated_by = EXCLUDED.updated_by,
                      updated_at = NOW()
                  RETURNING *`
        })
    });
    return response.json();
}
```

**Règles importantes :**

- **Quirk ResultSet Metabase** — les DDL (CREATE, DROP, ALTER) et DML sans RETURNING (INSERT, UPDATE, DELETE simples) s'exécutent mais Metabase renvoie une erreur (pas de result set). L'opération aboutit. Toujours utiliser `RETURNING` sur INSERT / UPDATE / DELETE pour une réponse propre, ou ignorer l'erreur pour les DDL.
- **Schéma** — toujours utiliser `matometa` (ex : `matometa.myapp_tracking`). Ne jamais créer de tables dans `public`.
- **Injection SQL** — l'exemple interpole des chaînes pour la clarté. En production, échapper les entrées utilisateur avant de les insérer dans le SQL. `/api/query` ne supporte pas les requêtes paramétrées — valider et échapper en JavaScript.
- **Pas de DDL depuis le frontend** — seul l'agent (Python) exécute CREATE TABLE / ALTER TABLE. Le frontend fait uniquement SELECT, INSERT, UPDATE, DELETE sur des tables existantes.

### Performance

#### Éviter les requêtes N+1

**Mauvais :**
```javascript
// NON : une requête par site
for (const siteId of siteIds) {
    const data = await query({
        source: 'matomo',
        instance: 'inclusion',
        method: 'VisitsSummary.get',
        params: { idSite: siteId, period: 'month', date: '2025-12' }
    });
}
```

**Bon :**
```javascript
// OUI : batcher avec idSite=all ou des date ranges
const data = await query({
    source: 'matomo',
    instance: 'inclusion',
    method: 'VisitsSummary.get',
    params: { idSite: 'all', period: 'month', date: '2025-12' }
});
```

#### Cache et debounce

```javascript
const cache = new Map();

async function cachedQuery(params) {
    const key = JSON.stringify(params);
    if (cache.has(key)) {
        return cache.get(key);
    }
    const result = await query(params);
    cache.set(key, result);
    return result;
}

function debounce(fn, delay = 300) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn(...args), delay);
    };
}

searchInput.addEventListener('input', debounce(async (e) => {
    const results = await cachedQuery({ ... });
    render(results);
}));
```

## Mise en forme

Police Marianne, palette DSFR et styles de base sont fournis par `style.css` du template. Ne pas réimporter la font ni redéfinir la palette. Pour toute extension, utiliser les variables CSS suivantes :

- **Accents :** `--navy`, `--periwinkle`, `--orange`, `--orange-light`
- **Palette étendue :** `--amber`, `--coral`, `--slate`, `--teal`, `--cyan`, `--red`
- **Sémantique :** `--text`, `--text-muted`, `--accent`, `--accent-hover`, `--link`

## Graphiques

### Chart.js (simple)

Désactiver l'animation initiale de Chart.js : elle tend à déformer la lecture des données. Les animations sont utilisables avec parcimonie et à propos.

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<canvas id="chart"></canvas>

<script>
new Chart(document.getElementById('chart'), {
    type: 'bar',
    data: {
        labels: ['Jan', 'Fév', 'Mar'],
        datasets: [{
            label: 'Visites',
            data: [120, 150, 180],
            backgroundColor: '#E57200'
        }]
    },
    options: {
        plugins: {
            legend: { display: false }
        }
    }
});
</script>
```

### D3.js / Observable Plot (complexe)

```html
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6"></script>

<div id="chart"></div>

<script>
const data = [
    { month: 'Jan', visits: 120 },
    { month: 'Fév', visits: 150 },
    { month: 'Mar', visits: 180 }
];

const chart = Plot.plot({
    marks: [
        Plot.barY(data, { x: 'month', y: 'visits', fill: '#E57200' })
    ],
    style: { fontFamily: 'Marianne' }
});

document.getElementById('chart').append(chart);
</script>
```

## Gestion d'erreur

```javascript
async function safeQuery(params) {
    try {
        const result = await query(params);
        if (!result.success) {
            showError(`Erreur : ${result.error}`);
            return null;
        }
        return result.data;
    } catch (e) {
        showError('Impossible de contacter le serveur');
        return null;
    }
}

function showError(message) {
    const el = document.getElementById('error');
    el.textContent = message;
    el.hidden = false;
}
```

## Accessibilité

- HTML sémantique (`<a>` ou `<button>`, pas `<div onclick>`)
- `aria-label` sur les boutons icône seule
- Contraste WCAG AA (4.5:1 pour le texte)
- Navigation clavier
- États de chargement et messages d'erreur explicites

## Déploiement (privé)

Les dashboards sont servis sous `/interactive/{dossier}/`. Pas d'étape de build — FastAPI sert les fichiers directement depuis `data/interactive/`.

```
/interactive/mon-dashboard/
```

**Toujours utiliser des URLs relatives** (commençant par `/`) pour lier vers des dashboards ou des fichiers.

## Modification

Un dashboard peut être modifié depuis n'importe quelle conversation, du moment que l'utilisateur précise lequel. Identifier le dossier concerné dans `data/interactive/`, appliquer les changements, puis **toujours donner à l'utilisateur l'URL relative du dashboard** (`/interactive/{dossier}/`) pour qu'il puisse constater la mise à jour directement.

## Tags valides

Valeurs contrôlées pour les champs `website` et `tags` d'`APP.md`.

### Produits (champ `website`)
- `emplois` — Emplois
- `dora` — Dora
- `marche` — Marché
- `communaute` — Communauté
- `pilotage` — Pilotage
- `plateforme` — Plateforme
- `rdv-insertion` — RDV-Insertion
- `mon-recap` — Mon Récap
- `multi` — Multi-produits

### Thèmes (champ `tags`)

**Acteurs :** `candidats`, `prescripteurs`, `employeurs`, `structures`, `acheteurs`, `fournisseurs`

**Concepts métier :** `iae`, `orientation`, `depot-de-besoin`, `demande-de-devis`, `commandes`

**Métriques :** `trafic`, `conversions`, `retention`, `geographique`

### Types de demande (champ `tags`)
- `extraction` — extraction de données
- `analyse` — analyse / rapport
- `meta` — méta / outillage

(`appli` est déprécié : tous les TDB sont des « applis » par définition désormais.)

### Sources (champ `tags`)
- `matomo`, `stats`, `datalake`, etc.

**Conventions sur les noms de tags** : lowercase, kebab-case (espaces → tirets). Les tags suivants ont été dépréciés/fusionnés et ne doivent pas être réutilisés : `appli`, `dashboard`, `dev`, `metabase`, `contact` (→ `contacts`), `orientations` (→ `orientation`), `rétention` (→ `retention`), `cross-produit` (→ `multi-produits`), `multi` (→ `multi-produits`).
