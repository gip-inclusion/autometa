# Matometa

Assistant analytics pour l'Inclusion (Matomo + Metabase → analyses en français).

```bash
make setup     # Environnement de développement complet (idempotent)
make doctor    # Diagnostic — une phrase actionnable par panne
make dev       # Serveur local (lance autometa)
make test      # Suite unit hermétique (aucun service requis)
make test-cov  # unit + integration + couverture fusionnée (Postgres + Redis requis)
make e2e       # Parcours de navigateur Playwright (exige une application servie)
make hooks     # Installe le hook git pre-commit (lint + suite unit)
make lint      # ruff check + format check
make format    # Auto-format
make migrate   # Migrations Alembic
make catalog   # Régénère les instantanés knowledge/catalog/ depuis les bases (identifiants requis)
make lint-js   # Biome sur web/static (JS et CSS) — le front n'a aucun test
make paved-road-status  # État du parcours, verdict de chaque critère
make ci        # lint + lint-js + security + migrations + test-cov + diff-cover
```

Architecture et flux de données : `.claude/ARCHITECTURE.md`.

Conventions de code : `.claude/rules/code.md`. Tests (pytest, pytest-mock, parametrize, factories) : `.claude/rules/tests.md`.

Après chaque tâche impliquant du code Python, relire `.claude/rules/` et vérifier que le code produit respecte toutes les conventions avant de considérer la tâche terminée. Corriger les violations trouvées sans attendre qu'on te le demande.

**Clarté de la demande** — Avant de répondre ou d'agir, se demander si la demande est claire (périmètre, résultat attendu). Si elle est ambiguë, demander à l'utilisateur de préciser plutôt que deviner ; si elle est claire, agir sans question superflue.

## Contexte métier

IAE (insertion par l'activité économique) — programme français d'emploi avec trois types d'acteurs :

- **Candidats** (demandeurs d'emploi) — Ont besoin d'un diagnostic pour obtenir un « pass IAE » valable deux ans. Candidatent via des prescripteurs ou en autonomie.
- **Prescripteurs** — Accompagnent les candidats. Les « prescripteurs habilités » peuvent réaliser des diagnostics et délivrer des pass.
- **Employeurs** (SIAE) — Structures employant les titulaires de pass. Nécessitent un conventionnement annuel.

**Bizdev / funnel AARRI** : pour tout terme d'étape bizdev (acquisition, activation, déploiement, rétention, adoption, référence, impact, pénétration, power user, maturité, acte métier…), consulter `knowledge/bizdev/glossaire.md`. Sans produit dans le contexte, appliquer la définition **générale** ; avec un produit (La plateforme de l'inclusion [ex Emplois], RDV-Insertion, Dora, Mon Récap, Le Marché), la définition **opérationnelle du produit**.

**Sources de données** — le choix de la source à interroger, l'ordre de priorité quand deux consignes divergent et le garde-fou d'accès vivent dans `AGENT.md` (sections « Sources de données » et « Quand deux consignes divergent »), injecté tel quel dans le prompt de l'agent de production. Ne pas les recopier ici : une copie diverge, et l'agent lit les deux fichiers. Le choix des tables d'`autometa_tables_db` vit dans le skill `autometa_tables_db`. `make test` vérifie ces règles (`lib/knowledge_lint.py`).

## Tableaux de bord interactifs

- Création **uniquement** via le skill `create_dashboard` (`--adopt` pour enregistrer un dossier existant). Jamais d'écriture directe dans `data/interactive/` pour un nouveau TDB.
- Plusieurs territoires ou entités sur un même écran → **TDB multi-sources** (une déclinaison par lien `?q=<jeton>`, un seul cron), à proposer puis à créer avec `--multi-source` **seulement après accord explicite**. Déclinaisons via `update_dashboard --add-variant`. Voir `docs/interactive-dashboards.md` § Mode multi-sources.
- Un `cron.py` ne tourne **que** si le TDB est enregistré avec `has_cron` — le système de cron lit la table `dashboards`.
- Persistance de données : schéma `dashboard_storage` de la DB applicative — frontend via `POST /api/query` `{source: "dashboard_storage", sql, params}`, agent et `cron.py` via `lib.dashboard_api.query_storage` (la façade, seul import autorisé dans un TDB). Voir `docs/interactive-dashboards.md` § Persistance.
- En prod, un hook de garde bloque les écritures **Edit/Write** hors de `data/`, `.claude/` et `/tmp`. De toute façon `web/`, `lib/`, `knowledge/`, etc. sont baked dans l'image : toute modification (y compris via Bash, non couvert par le hook) est éphémère et perdue au redéploiement.
- Scratchpad → `/tmp`. Fichiers one-off téléchargeables (csv, xlsx…) → racine de `data/interactive/`, jamais de `.html` hors TDB.

## Sites web

Tableau des sites (nom, URL, ID Matomo, fiche knowledge) : `AGENT.md`, section « Sites web » — seule référence, vérifiée par `make test`.

## Chemins clés

| Chemin | Rôle |
|---|---|
| `config/sources.yaml` | Configuration des sources de données |
| `knowledge/sites/` | Contexte par site — lire avant de requêter |
| `knowledge/matomo/README.md` | Référence API Matomo |
| `data/cache/matomo/` | Baselines Matomo par site (synchro quotidienne depuis PostgreSQL) |
| `data/cache/metabase/` | Inventaire cartes et dashboards Metabase (synchro quotidienne) |
| `knowledge/data_inclusion/README.md` | Architecture pipeline data·inclusion (dbt layers, sources, traçabilité) |
| `DATABASE_URL` (PostgreSQL) | Conversations, rapports, files d'attente agent, etc. |
| `data/interactive/` | Fichiers téléchargeables (servis à `/interactive/`) |

## Dépôts GitHub

Dépôts et branches des produits : `AGENT.md`, section « Dépôts GitHub ».

## Session Ledger

| Date | Type | Summary | Lesson |
|------|------|---------|--------|
| 2026-09-18 | feat | verify_dashboard via paved road contract-first (branche alexis/feat/viz-quality-paved) : 14 DOD, 12 démontrés, lentille convergée en 3 passes | Dans un worktree git, le hook pre-commit échoue : GIT_INDEX_FILE absolu fait écrire tests/test_lint_baseline.py dans l'index réel — committer depuis un clone ordinaire hors /tmp. Un Chart.js/Plot vide dessine ses axes : juger les séries, pas les pixels. |
| 2026-10-16 | fix | Review #230 (cdarnispro) : polices/images/médias en avertissement + écho CORS ignoré (le gabarit officiel passe) ; Chart.js jugé sur la valeur calculée de l'axe des valeurs (horizontal, `parsing`) ; axes D3 (`g.tick`, `path.domain`) écartés. Tests contre Chart.js 4.5.1 et D3 7.9.0 réels servis hors réseau (`browser/fixtures`). Preuve Docker : non root + /dev/shm 64 Mo OK, image +919,6 Mo | Sur Chart.js réel, une barre null n'a **pas** de `skip` (seuls ligne/radar le posent) et un camembert lit null comme 0 : `!el.skip` seul laisse passer `[null, NaN]` — sonder la vraie lib avant de reprendre une suggestion de review. Image fraîche : `.venv/bin/python skills/…` → `No module named 'lib'` (`uv sync --no-editable` avant COPY) ; c'est le `uv run` du CMD qui réinstalle en editable. Hook pre-commit : le clone ordinaire doit être **hors /tmp** (la garde d'écriture autorise /tmp, test_hook_settings échoue). |
| 2026-10-16 | fix | Port vers #230 des apprentissages de #228 : Chromium sur Scalingo (apt-buildpack + `Aptfile` + `bin/install_playwright_browser.sh` via `post_compile`), code 2 « audit impossible » si le navigateur ne démarre pas, graphiques d'onglets inactifs comptés, séries et libellés Chart.js jugés, isolation de `test_lint_baseline` | L'`Aptfile` de #228 cassait le build sur scalingo-24 : `libasound2` y est un paquet virtuel sans candidat (renommé `libasound2t64`) — `libasound2-dev` existe sur les deux stacks. Rejouer le vrai `apt-buildpack/bin/compile` dans `scalingo/scalingo-2x` (non root, `HOME=/app`, puis runtime sans/avec `.profile.d`) prouve un build sans déployer. Ne lister que les libs que `ldd` dit manquantes : chaque paquet est réinstallé sous .apt, devant celles du système. Un jeu de données Chart.js sans `label` dessine « undefined » en légende. pre-commit met de côté les modifs non indexées mais pas les fichiers non suivis : un test non suivi qui dépend d'un fichier modifié échoue au commit. |
| 2026-11-04 | feat | PR 3a agents (branche feat/agents-arsenal) : liste fermée `config/agent_destinations.yaml`, validateur `pdi.agent/1` réduit (`lib/agent_config.py`), livraison Slack et Notion par mode ombre / relecture / réel (`lib/agent_delivery.py`), journaux sans contenu | Le worker de job n'a aucun accès à Autometa : c'est Autometa qui livre la sortie du run, le worker ne détient aucun jeton. Le hook `.claude/hooks/check_python.py` compte `{where}` comme le mot-clé SQL WHERE dans une f-string : nommer la variable autrement. Le hook pre-commit partagé pointe vers un venv d'un autre worktree : committer avec `PATH=$PWD/.venv/bin:$PATH`. `.github/CODEOWNERS` est en écriture refusée pour l'agent. |
| 2026-11-04 | feat | PR 3b agents (branche feat/agents-arsenal-confirm, empilée sur 3a) : création d'agent par proposition / création / retrait (`lib/agents.py`, skill `agents`), confirmation vérifiée par le code, livraison d'un run, approbation des envois en relecture | La règle « jamais apply dans le tour du plan » se vérifie dans le code : noter l'id du dernier message utilisateur de `AUTOMETA_CONVERSATION_ID` à la proposition, exiger un id plus grand dans la même conversation à la confirmation. Le parcours paved road s'arrête à l'état align sans validation humaine du contrat : pas d'attestation avant. Base de test jetable : `pgvector/pgvector:pg16` sur 127.0.0.1:55439, `DATABASE_URL=… pytest -m integration`. |
| 2026-11-04 | feat | PR 4 agents (branche feat/agent-boamp, empilée sur #278) : agent veille BOAMP déclaré dans le dépôt (`agents/veille-boamp.yaml` + consigne `.md`), en ombre vers `bizdev.marche` ; `tests/test_agents_repo.py` valide tout `agents/*.yaml` dans le couloir unit | `Makefile`, `scripts/check_*.py` sont en deny pour l'agent (Edit, sed **et** rm) : un contrôle CI neuf se loge dans un test de `make test`, jamais dans un script `check_*` créé par heredoc. API BOAMP Explore v2.1 : `search(objet, …)`, `etat="INITIAL"`, `type_marche="SERVICES"` marchent en `where` ; ~1 150 avis services+fournitures par semaine. |
| 2026-11-04 | sec | PR 3a agents : bot Slack dédié (`AGENT_SLACK_BOT_TOKEN`, sans repli sur `SLACK_BOT_TOKEN`) et avertissement au démarrage des écarts entre `config/agent_destinations.yaml` et `AGENT_DESTINATION_TARGETS` | `lib/notion.py` lit `NOTION_TOKEN` comme global de module dans `notion_request` : un jeton Notion par appelant demande de le faire passer par toutes ses fonctions. Un worktree sous `/tmp` fait échouer `test_the_write_guard_still_blocks_when_started_outside_the_project` au pre-commit : le créer sous `~`. |
| 2026-11-04 | feat | PR 3b v2 agents : classificateur `clef` (Ollama Cloud, `/v1/systemone`, appelé par Autometa après le run), préparations par crons de `cron/` (liste fermée, dans l'ordre, sorties en `input_uri`), cadence et cron générique (revu ensuite en `cron/run-agents`), commande `destinations` du skill | « Process exited with code -9 » sans stderr : Autometa ne tue le CLI que sur annulation, budget ou arrêt, chacun laisse une autre trace ; le -9 vient de l'extérieur (mémoire du conteneur). `clef` répond `answers.<nom>.noul` = probabilité du oui. `autometa-jobs` n'a aucun déclenchement sur horaire : Autometa déclenche. Un cron ne tourne jamais dans le processus web (`/api/cron/<slug>/run` passe par `start_one_off` de `web/scalingo.py`). |
| 2026-11-04 | feat | PR 3b v2 révisée (complément d'Alexis) : un seul cron générique `cron/run-agents` (lot `maintenance`), préparations typées fermées (`notion`, `s3`, `cron` = dernière sortie réussie lue dans `cron_runs`, jamais relancée), lancement et modification d'un agent par confirmation vérifiée par le code, plus de conteneur one-off | `lib/jobs.py` n'a ni déclenchement sur horaire ni mise à jour de pipeline : une consigne changée crée `agent-<slug>-v<n>`. Un identifiant de proposition à la seconde près entre en collision dès qu'on propose deux modifications d'affilée : suffixe aléatoire. `tests/test_knowledge_consistency.py` vérifie les chemins cités dans le ledger : renommer un dossier oblige à corriger les lignes qui le citent. |
