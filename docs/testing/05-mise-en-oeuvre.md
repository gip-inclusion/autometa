# Mise en œuvre : le runbook pour démarrer (et reprendre)

Document **exécutable et autoportant**. Si tu reprends ce chantier à froid (nouvelle session, autre personne, autre agent), tu commences ici. Il répond à : quelle stratégie projet, comment ça s'insère dans le dépôt existant, comment savoir qu'une phase est *finie*, et quelle est la prochaine action concrète.

Les autres docs restent la référence : le **pourquoi** ([`01-pourquoi.md`](01-pourquoi.md)), la **stratégie technique** ([`02-strategie.md`](02-strategie.md)), l'**ordre/dépendances** ([`03-roadmap.md`](03-roadmap.md)), le **détail de chaque phase** ([`04-phases.md`](04-phases.md)).

---

## 1. Contexte pour reprise à froid

- **But** : non-régression + anti-slop dans un repo développé massivement par des agents IA. On convertit des règles (espoirs) en vérifications déterministes (lois), chacune posant un **cliquet** qui ne peut que monter.
- **Modèle mental** : la dette existante est **assumée** ; on l'**empêche de grossir** et on **gèle son niveau** (phases 1–4), puis on la **rembourse** par zones verrouillées (phases 5–8). Détail : [`01-pourquoi.md`](01-pourquoi.md).
- **État du dépôt au démarrage** (vérifié) :
  - ~80 fichiers de tests à plat dans `tests/` ;
  - `pytest.ini` : un seul marqueur `integration` (définition obsolète) ; bloc `markers` **dupliqué** dans `pyproject.toml` ;
  - `tests/conftest.py` crée la base **à l'import** → l'unit n'est pas hermétique ;
  - la CI **mesure déjà** la couverture (`--cov=web --cov=lib`) mais ne la **bloque pas** ;
  - **aucun** vérificateur de types ; **aucun** Pydantic dans `web/`/`lib/` ;
  - `make ci` = `lint security check-migrations test` ; CI = jobs `lint`, `security`, `test`, `migrations`, `docker`.

## 2. Stratégie projet

- **Une phase = une PR** (ou un petit lot cohérent). Pas de big-bang. Chaque PR pose **un** cliquet et est mergeable seule.
- **On peut s'arrêter après n'importe quelle phase** en étant strictement plus sûr qu'avant. Les phases 1–4 (geler + fail fast) sont l'essentiel ; le reste est du remboursement à la cadence choisie.
- **Parallélisme** : la fondation contrats (phase 6) est un **track indépendant**, lançable dès le départ. Le rangement (phase 7) est le plus repoussable. Cf. la carte de [`03-roadmap.md`](03-roadmap.md).
- **Gouvernance du cliquet** : un plancher (couverture, seuil diff, périmètre typé, score de mutation) **ne se relève que dans la PR qui l'améliore, jamais à la baisse**. Une PR qui veut baisser un plancher = revue humaine obligatoire.
- **Zones critiques** : toute phase touchant `web/models.py`, `alembic/`, `web/runner.py`, `web/agents/base.py`, `.claude/settings.json`, etc. (cf. `.claude/rules/zones-critiques.md`) exige une relecture humaine — à signaler dans la PR.

### Charge, gain et parallélisme

Pour piloter. Unité de charge : **jours-dev** en fourchette **basse–haute** (l'agent fait le gros, l'humain relit/pilote ; l'overhead de relecture des zones critiques ⚠️ est inclus dans la borne haute). Le **gain** est une part du gain total (non-régression + anti-slop), pondérée selon la priorité des docs. Estimations **indicatives** : recaler la charge réelle dans la PR de chaque phase.

**Gain et charge par phase**

| Phase | Charge (j) | Gain | Gain cumulé |
|---|---|---|---|
| 1 — Geler le plancher | 1–2 | 18 % | 18 % |
| 2 — Couverture du diff *(levier n°1)* | 0,5–1 | 20 % | 38 % |
| 3 — Détecteurs de slop | 1,5–2 | 12 % | 50 % |
| 4 — Hooks fail-fast ⚠️ | 2–3,5 | 10 % | 60 % |
| 5 — Unit hermétique + découpe CI | 3–5 | 8 % | 68 % |
| 6 — Contrats : types *(track parallèle)* | 4,5–8,5 | 12 % | 80 % |
| 7 — Rangement *(repoussable)* | 3,5–5,5 | 5 % | 85 % |
| 8 — Profondeur (mutation, évals, données) | 6,5–10,5 | 15 % | 100 % |

**Découpage en tâches (1 tâche ≈ 1 PR)**

| Phase | Tâche (PR) | Charge | Dépend de | Track |
|---|---|---|---|---|
| **1** | 1a · baseline branches + marqueurs (`pytest.ini`, purge bloc dupliqué, `pytest-cov`, `branch=true`) | 0,5–1 j | — | A |
| | 1b · CI `--cov-fail-under=baseline` + test négatif (`make ci` rougit si baisse) | 0,5–1 j | 1a | A |
| **2** | 2a · `diff-cover` bloquant (`--fail-under=90`, `--compare-branch=origin/main`) | 0,5–1 j | 1b | A |
| **3** | 3a · config ruff (`PT`, `B011`, per-file-ignores) dans `make lint` | 0,5 j | — | A |
| | 3b · `scripts/check_test_quality.py` (AST) + lint/pre-commit + ses tests | 1–1,5 j | 3a | A |
| **4** | 4a · `PostToolUse` ruff sur `.py` édité (nudge) | 0,5–1 j | 3b | A |
| | 4b · `Stop` : suite unit + traçabilité source→test, bloque si rouge (convergence) | 1–2 j | 4a | A |
| | 4c · `PreToolUse` étendu aux zones critiques | 0,5 j | 4a | A |
| **5** | 5a · `conftest` lazy (base hors import, découpler l'`autouse` session) — *transverse* | 2–3 j | — | A |
| | 5b · découpe CI unit/integration + `coverage combine` + Makefile (**même PR** — couplage n°1) | 1–2 j | 5a, 1b | A |
| **6** | 6a · mypy + job CI + `make typecheck` + façade strict (`lib/query`, `web/config`) | 1,5–2,5 j | — | **B** |
| | 6b · élargissement au cliquet (liste de modules stricts, continue) | 1–3 j | 6a | **B** |
| | 6c · Pydantic aux frontières (Matomo/Metabase, `/api/query`, `dashboard_storage`) | 2–3 j | 6a | **B** |
| **7** | 7a · arbo miroir `tests/web` `tests/lib`… + conftest racine + per-file-ignores | 1,5–2,5 j | — | A (fin) |
| | 7b · `respx`/`MockTransport` (remplace le mock S3 interne) + `factories.py` | 1,5–2,5 j | — | A (fin) |
| | 7c · `truncate` dérivé de `Base.metadata` | 0,5 j | 5a | A (fin) |
| **8** | 8a · circuit déterministe LLM : transcripts `.jsonl` + `pytest-subprocess` + snapshot `syrupy` | 1,5–2,5 j | 5b | A |
| | 8b · mutation nightly (`mutmut` sur diff/modules critiques) + `nightly.yml` | 1–2 j | suite verte | A |
| | 8c · évals `promptfoo` (~20 cas + juge LLM), non bloquant | 2–3 j | — | A/B |
| | 8d · justesse données : golden datasets + invariants + cohérence inter-sources | 2–3 j | 5b | A |

⚠️ = zone critique (relecture humaine obligatoire, incluse dans la borne haute).

**Parallélisme — 2 tracks**

```
Track A (tests / CI, séquentiel par dépendances) — 1 personne
  [1a·1b]→[2a]→[3a·3b]→[4a·4b·4c]→[5a·5b]→[8a·8b·8d]      ⋯ [7a·7b·7c] repoussable
   plancher  diff   slop    hooks     hermét.   profondeur        rangement

Track B (contrats, INDÉPENDANT, démarre jour 1) — 1 personne
  [6a]→[6b élargissement continu]→[6c Pydantic frontières]
   façade strict

Points de jonction :
  • 5b a besoin de 1b (fusion couverture ⟺ plancher — même PR)
  • 8c (évals) peut être portée par le track B (agent) sans bloquer A
  • 6c (Pydantic /api/query, dashboard_storage) gagne à venir après 5, sinon autonome
```

**Fenêtres (jours ouvrés, 2 personnes en parallèle)**

| Jalon | Fenêtre basse | Fenêtre haute |
|---|---|---|
| Fin phase 4 → dette gelée + fail-fast (~60 % du gain) | j5 | j8,5 |
| Fin phase 5 → unit hermétique, boucle rapide | j8 | j13,5 |
| Fin phase 8 → profondeur (hors rangement) | j14,5 | j24 |
| Track B (contrats) terminé — *hors chemin critique* | j5 | j8,5 |
| Phase 7 (rangement, si retenue) | +3,5 j | +5,5 j |

- **Charge totale** (deux tracks, phase 7 incluse) : **~22,5–38 j-dev**.
- **Calendrier à 2 personnes** : **~14,5–24 j ouvrés** (phase 7 reportée) — le track B est masqué par le track A, donc gratuit en calendrier.
- **À 1 personne** (séquentiel) : ~18,5–33 j.
- **Où couper** : le coude de rentabilité est à **fin phase 4** (~60 % du gain, j5–8,5). Phase 7 est la variable d'ajustement (aucune dépendance amont/aval).
- **Ce qui pousse vers le haut de fourchette** : 5a (chantier transverse), 4b (convergence du hook `Stop` + relecture zone critique), phase 8 (largeur : 4 sous-chantiers).

## 3. Carte d'intégration au dépôt

Où chaque phase s'insère dans les fichiers existants. (✏️ = modifié, ➕ = créé.)

| Fichier / emplacement | Phases | Quoi |
|---|---|---|
| `pytest.ini` ✏️ | 1, 5 | marqueurs (`integration`/`e2e`/`external`), `--strict-markers --strict-config` |
| `pyproject.toml` ✏️ | 1, 3, 6, 8 | retirer bloc `markers` dupliqué ; `[tool.ruff.lint]` (PT, B011, per-file-ignores) ; `[tool.coverage.run] branch=true` ; `[tool.mypy]` ; deps dev (`pytest-cov`, `diff-cover`, `mypy`, `mutmut`, `respx`, `pytest-subprocess`, `syrupy`, `hypothesis`) |
| `Makefile` ✏️ | 1, 5, 6 | cibles `test-unit`, `test-cov`, `typecheck` ; `ci` enrichi |
| `.github/workflows/ci.yml` ✏️ | 1, 2, 5, 6 | `--cov-fail-under` + `--cov-branch` ; step `diff-cover` ; split job `test` → `unit` (sans services) + `integration` ; `coverage combine` ; job `typecheck` |
| `.github/workflows/nightly.yml` ➕ | 8 | `external` + mutation + évals ; secrets injectés **ici uniquement** |
| `.claude/settings.json` ✏️ | 4 | hooks `PostToolUse` / `Stop` / `PreToolUse` (zone critique) |
| `.pre-commit-config.yaml` ✏️/➕ | 3, 5 | ruff, `check_test_quality`, pytest-unit |
| `scripts/check_test_quality.py` ➕ | 3 | détecteur AST de tests creux |
| `tests/conftest.py` ✏️ | 5, 7 | DB lazy ; `truncate` dérivé de la metadata |
| `tests/factories.py` ➕ | 7 | fonctions `create_*(session, …)` |
| `tests/web/` `tests/lib/` … ✏️ | 7 | restructuration miroir |
| `.claude/rules/tests.md` ✏️ | 4, 8 | conventions (transcripts, fakes, dual-track) |
| `.claude/skills/tdd/` ➕ | 4 | skill red → confirme l'échec → commit tests → green |
| `.claude/agents/test-reviewer.md` ➕ | 4/8 | sous-agent reviewer (Read/Grep/Glob, contexte vierge) |
| `evals/` ➕ | 8 | `promptfoo` + cas |
| `lib/query.py`, `web/config.py` ✏️ | 6 | premiers modules en typage strict (façade) |

## 4. Définition de « fait » par phase

Comment savoir qu'un cliquet est **verrouillé** (et donc qu'on peut passer à la suite). Le test décisif : *une PR qui viole la garantie doit échouer.*

| Phase | « Fait » quand… | Preuve (test négatif) |
|---|---|---|
| 1 | plancher de couverture (branches) actif + marqueurs stricts | une PR qui supprime un test ou descend sous le plancher → **CI rouge** ; un marqueur mal écrit → **collecte rouge** |
| 2 | couverture du diff active | une PR ajoutant une ligne non couverte → **diff-cover rouge** |
| 3 | détecteurs de slop dans `make lint` + pre-commit | un test sans assertion / tautologique → **lint rouge** |
| 4 | hooks en place | éditer un `.py` fautif → l'agent reçoit l'erreur ; conclure avec suite rouge / source sans test → **Stop bloque** |
| 5 | job unit **sans Postgres** vert + couverture fusionnée | lancer `-m "not integration"` sans service → **vert** ; le plancher tient toujours |
| 6 | job typecheck vert, façade en strict | renommer un symbole de `lib.query` → **typecheck rouge** |
| 7 | arbo miroir + truncate dérivé | ajouter un modèle sans toucher au conftest → pas de fuite entre tests ; test d'un module trouvable mécaniquement |
| 8 | mutation nightly + évals nightly + golden datasets | rapport de mutants produit ; éval tourne (non bloquante) ; un test data assert un chiffre connu |

## 5. Prochaine action : Phase 1, déroulée

La plus rentable, presque sans churn. Étapes ordonnées :

1. **Mesurer la baseline** : lancer la suite avec couverture **de branches** et noter le pourcentage.
   ```
   uv run --frozen pytest -m "not integration" --cov=web --cov=lib --cov-branch -q
   ```
2. **`pytest.ini`** : déclarer les 3 marqueurs + `addopts = --strict-markers --strict-config` (cf. snippet [`04-phases.md`](04-phases.md#phase-1)).
3. **`pyproject.toml`** : supprimer le bloc `[tool.pytest.ini_options].markers` dupliqué ; ajouter `pytest-cov` aux deps dev ; `[tool.coverage.run] branch = true`.
4. **CI (`ci.yml`, job `test`)** : ajouter `--cov-branch --cov-fail-under=<baseline>` et basculer le filtre vers `-m "not external"` **seulement si** les marqueurs `e2e`/`external` sont déjà posés ; sinon rester sur `-m "not integration"` pour cette phase.
5. **`make ci`** : vérifier qu'il échoue bien si on baisse artificiellement la couverture (test négatif de la section 4).
6. **PR** : titre « test: gel du plancher de couverture + hygiène marqueurs » ; mentionner que c'est la phase 1 de `docs/testing`.

> Choix à figer dans cette PR : **couverture de branches** (pas de lignes), pour ne jamais avoir à re-baseliner (couplage n°2 de [`03-roadmap.md`](03-roadmap.md)).

Pour les phases suivantes : suivre l'ordre de [`03-roadmap.md`](03-roadmap.md), le détail/artefacts de [`04-phases.md`](04-phases.md), et valider chaque fois la « définition de fait » (section 4).

## 6. Protocole de reprise (où en est-on ?)

Pour qu'une session future retrouve l'état sans deviner, **inspecter les artefacts** plutôt que la mémoire :

1. `pytest.ini` contient-il `--strict-markers` et les 3 marqueurs ? → phase 1 entamée.
2. `ci.yml` contient-il `--cov-fail-under` ? → phase 1 faite. Un step `diff-cover` ? → phase 2 faite.
3. `scripts/check_test_quality.py` existe-t-il ? → phase 3 faite.
4. `.claude/settings.json` a-t-il des hooks `Stop`/`PostToolUse` ? → phase 4 faite.
5. Existe-t-il un job CI **sans services** qui passe ? → phase 5 faite.
6. Job `typecheck` + `[tool.mypy]` ? → phase 6 entamée (voir la liste des modules stricts).
7. `tests/web/` / `tests/lib/` peuplés ? → phase 7 faite.
8. `nightly.yml` + `evals/` ? → phase 8 entamée.

La prochaine phase = la première dont la « définition de fait » (section 4) n'est pas satisfaite. Reprendre à la section 5 mais pour cette phase.
