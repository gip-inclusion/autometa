# Autometa

Assistant IA pour l'analyse des données métier de la Plateforme de l'inclusion.

Autometa combine les APIs **Matomo** (analytics web) et **Metabase** (données métier) pour répondre aux questions sur l'usage des services numériques de la Plateforme.

## Fonctionnalités

- **Conversations en langage naturel** — Posez des questions sur le trafic, les candidatures, les utilisateurs
- **Requêtes automatisées** — L'agent écrit et exécute des scripts Python pour interroger les APIs
- **Rapports structurés** — Génération de rapports Markdown avec graphiques Mermaid
- **Base de connaissances** — Documentation des sites, métriques et tables de données

## Structure du projet

```
.
├── knowledge/           # Base de connaissances (Markdown)
│   ├── sites/           # Documentation par site (emplois.md, pilotage.md, etc.)
│   ├── matomo/          # Référence API Matomo
│   ├── metabase/        # Référence API et tables Metabase
│   └── stats/           # Métriques et indicateurs dans Metabase
│
├── skills/              # Compétences de l'agent (skills Claude Code)
│   ├── matomo_query/    # Interrogation API Matomo
│   ├── metabase_query/  # Interrogation API Metabase
│   ├── save_report/     # Sauvegarde de rapports
│   └── sync_*/          # Synchronisation des données de référence
│
├── web/                 # Application web FastAPI
│   ├── agents/          # Backends agent (CLI, SDK)
│   ├── routes/          # Endpoints API et pages HTML
│   ├── templates/       # Templates Jinja2
│   └── static/          # CSS, JS, assets
│
├── data/                # Données runtime (gitignored)
│   ├── scripts/         # Scripts one-off générés par l'agent
│   └── interactive/     # Fichiers téléchargeables (servis à /interactive/)
│
├── reports/             # Rapports générés
│
├── CLAUDE.md            # Instructions projet + prompt agent
└── docker-compose.yml   # Déploiement production
```

## Extensibilité

### Ajouter des connaissances

Les fichiers Markdown dans `knowledge/` sont lus par l'agent en fonction de la requête.
L'agent utilisera automatiquement ces informations pour contextualiser ses réponses.

### Créer un skill

Les skills sont des instructions réutilisables pour l'agent. La structure reprend [la spécification officielle](https://agentskills.io/) :

```
skills/mon_skill/
├── SKILL.md             # Instructions (lu par l'agent)
└── scripts/
    └── mon_script.py    # Code Python appelable
```

### Modifier le comportement de l'agent

Le fichier `CLAUDE.md` contient le system prompt. Sections clés :

- **Domain Context** — Vocabulaire métier (IAE, SIAE, prescripteurs, etc.)
- **Query Workflow** — Processus de réponse aux questions
- **Presenting Options** — Format des boutons d'action
- **Container Environment** — Chemins et restrictions en production

## Installation locale

### Prérequis

- Python 3.14+
- Node.js 20+ (pour Claude Code CLI)
- Clés API : `MATOMO_TOKEN`, `METABASE_USER`, `METABASE_PASSWORD`

### Setup

```bash
# Cloner le repo
git clone https://github.com/gip-inclusion/Matometa.git
cd Matometa

# Environnement Python
python -m venv .venv
source .venv/bin/activate
uv sync

# Variables d'environnement
cp .env.example .env
# Éditer .env avec vos credentials

# Installer Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Lancer l'application
make dev
```

L'interface est accessible sur http://127.0.0.1:5000

### Configuration

Toutes les variables sont documentées dans `.env.example`. Voici les groupes principaux :

| Groupe | Variables | Requis |
|--------|-----------|--------|
| **Agent** | `AGENT_BACKEND`, `CLAUDE_CODE_OAUTH_TOKEN` | Oui |
| **Web** | `ADMIN_USERS`, `BASE_URL` | Oui |
| **Base de données** | `DATABASE_URL` | Oui (PostgreSQL requis) |
| **S3** | `S3_BUCKET`, `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | Non (fichiers locaux) |
| **Sources de données** | `MATOMO_API_KEY`, `METABASE_*_API_KEY`, `NOTION_TOKEN`, `GRIST_API_KEY` | Selon `config/sources.yaml` |
| **Claude CLI** | `CLAUDE_CLI`, `CLAUDE_CODE_OAUTH_TOKEN`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | Quand `AGENT_BACKEND=cli` |
| **Conteneur** | `CONTAINER_ENV` | Scalingo / PaaS |
| **OAuth2-Proxy** | `OAUTH2_PROXY_*` | Quand on utilise le buildpack oauth2-proxy |

## Déploiement

### Docker (auto-hébergé)

```bash
docker compose up -d

# L'app écoute sur 127.0.0.1:5002
# Configurer un reverse proxy (nginx, Caddy) pour l'exposer
```

### Scalingo

L'application tourne sur Scalingo dans un seul conteneur web.

```bash
# Créer l'application
scalingo create matometa

# Ajouter PostgreSQL
scalingo addons-add postgresql postgresql-starter-512

# Variables obligatoires
scalingo env-set AGENT_BACKEND=cli
scalingo env-set CLAUDE_CODE_OAUTH_TOKEN=xxx
scalingo env-set ADMIN_USERS=user@example.com
scalingo env-set CONTAINER_ENV=1

# Sources de données (selon config/sources.yaml)
scalingo env-set MATOMO_API_KEY=xxx
scalingo env-set METABASE_STATS_API_KEY=xxx
scalingo env-set METABASE_DATALAKE_API_KEY=xxx

# Stockage S3 (recommandé — le filesystem Scalingo est éphémère)
scalingo env-set S3_BUCKET=matometa
scalingo env-set S3_ENDPOINT=https://s3.fr-par.scw.cloud
scalingo env-set S3_ACCESS_KEY=xxx
scalingo env-set S3_SECRET_KEY=xxx

# OAuth2-Proxy (optionnel — auth Google)
scalingo env-set OAUTH2_PROXY_PROVIDER=google
scalingo env-set OAUTH2_PROXY_CLIENT_ID=xxx
scalingo env-set OAUTH2_PROXY_CLIENT_SECRET=xxx
# ... voir .env.example pour la liste complète

# Déployer
git push scalingo main
```

**Variables automatiques Scalingo :**
- `DATABASE_URL` : fournie par l'addon PostgreSQL
- `PORT` : port d'écoute (utilisé par oauth2-proxy)

**Fichiers de configuration :**
- `Procfile` : uvicorn derrière oauth2-proxy
- `.buildpacks` : Python + oauth2-proxy
- `.python-version` : version Python
- `pyproject.toml` / `uv.lock` : dépendances (uv)

#### Staging

App Scalingo parallèle `autometa-staging`, addon PostgreSQL dédié, variables d'env configurées comme la prod (cf. `.env.example`).

**Flux de déploiement** :

| Workflow | Trigger | Cible |
|---|---|---|
| `deploy-staging.yml` | `push` sur `main` | `autometa-staging` |
| `deploy-prod.yml` | `push` d'un tag `v*` | `matometa` (prod) |

Les deux délèguent la mécanique au workflow réutilisable `_deploy.yml`. Pour shipper en prod : tagger un commit déjà déployé en staging (`git tag vYYYY.MM.DD && git push origin vYYYY.MM.DD`).

**Authentification CI** : secret repo `SCALINGO_SSH_KEY` (clé privée). La clé publique correspondante doit être déclarée sur chaque app via `scalingo --app <name> keys-add`.

## Développement

```bash
make dev        # Serveur local (lance autometa)
make test       # Tests unitaires
make lint       # Vérification ruff
make format     # Auto-format
make migrate    # Appliquer les migrations Alembic
make ci         # lint + security + test
```

### Commandes installées

| Commande | Description |
|----------|-------------|
| `autometa` | Lance le serveur web |
| `sync-sites` | Synchronise les baselines Matomo → PostgreSQL + warmup |
| `sync-inventory` | Synchronise l'inventaire Metabase → PostgreSQL + warmup |

### Backend Ollama (local, sans clé API)

```bash
# Démarrer Ollama (Docker ou natif)
docker compose --profile ollama up -d
# ou: ollama serve

# Lancer l'app avec le backend Ollama
AGENT_BACKEND=cli-ollama make dev
```

Variables Ollama configurables dans `.env` : `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_REQUEST_TIMEOUT`.

### Evals

Comparer les réponses entre backends (Claude vs Ollama) :

```bash
docker compose --profile ollama up -d
.venv/bin/python evals/run_eval.py
```

Les résultats sont stockés dans `evals/` (gitignored).

## Licence

Projet interne GIP Plateforme de l'inclusion.
