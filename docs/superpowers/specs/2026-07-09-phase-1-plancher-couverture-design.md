# Phase 1 — Geler le plancher de couverture + hygiène des marqueurs

Design validé le 2026-07-09. Concrétise la **Phase 1** de `docs/testing/` pour ce dépôt.
Référence stratégique : `docs/testing/04-phases.md` (§Phase 1) et `docs/testing/05-mise-en-oeuvre.md` (§5).

## But

Poser la première marche de la stratégie de test : **geler le niveau de qualité actuel**
pour que la dette ne puisse plus grossir en silence. On n'améliore pas la couverture ici —
on interdit qu'elle **baisse**. Deux cliquets :

1. **Plancher de couverture** (branches) : la CI rougit si la couverture descend sous la baseline.
2. **Hygiène des marqueurs** : config unique et stricte ; un marqueur mal orthographié casse la collecte.

Les deux cliquets sont **monotones** : ne se relèvent que dans la PR qui les améliore, jamais à la baisse.

## État constaté (vérifié le 2026-07-09)

- `pytest.ini` : marqueur `integration` seul, définition obsolète (« Matomo credentials »).
- `pyproject.toml` : bloc `[tool.pytest.ini_options].markers` **dupliqué** et divergent
  (mort — `pytest.ini` a la priorité).
- CI job `test` : mesure déjà la couverture (`--cov=web --cov=lib`) mais **sans**
  `--cov-fail-under` ni `--cov-branch` ; `pytest-cov` injecté via `--with 'pytest-cov>=7'`.
- Seul marqueur custom réellement utilisé : `integration` (25 occurrences).
  `parametrize`/`usefixtures` sont des builtins → `--strict-markers` ne casse rien.
- Aucun usage de PostGIS (web/lib/alembic) : l'image CI `postgis/postgis:18-3.6` est un
  sur-ensemble inutilisé ; `postgres:18` nu suffit.

## Parité d'environnement (local ≡ CI)

Mesure faite en local, environnement confirmé équivalent au gate CI :

| Composant | CI | Local | Verdict |
|---|---|---|---|
| Python | 3.14 | 3.14.6 CPython | ✅ |
| Redis | `redis:7-alpine` :6379 | `souverainet-redis-1` :6379 | ✅ |
| Postgres | `postgis/postgis:18-3.6` :5432 | `souverainet-db-1` = `postgres:18` :5433 | ✅ (PostGIS non requis) |
| Identifiants | `autometa:autometa` / `autometa_test` | idem | ✅ |

Commande de mesure (local) :
```
DATABASE_URL=postgresql://autometa:autometa@localhost:5433/autometa \
REDIS_URL=redis://localhost:6379/0 \
uv run --frozen --with 'pytest-cov>=7' pytest tests/ -q -m "not integration" \
  --cov=web --cov=lib --cov-branch --cov-report=term
```

## Baseline mesurée

**Couverture de branches = 74,90 %** (1401 tests verts, 45 items `integration` désélectionnés, 0 échec).

Décision figée : **plancher à `74.90` avec `precision = 2`** (gèle pile au mesuré, fidèle au cliquet).
Repli documenté : `74` (entier) si un rouge flaky apparaît.
`term` affichait « 75 % » par arrondi — figer 75 aurait rendu la CI rouge d'emblée (74,90 < 75).

Décision figée : **couverture de branches, pas de lignes** — une seule fois, pour ne jamais re-baseliner
(couplage n°2 de `docs/testing/03-roadmap.md`).

## Changements

### `pytest.ini` (source unique de vérité)
```ini
[pytest]
testpaths = tests
addopts = --strict-markers --strict-config
markers =
    integration: a besoin de Postgres + Redis (TestClient, fakeredis)
    e2e: parcours complet en process (runner + Redis + SSE, agent faké)
    external: vrais services externes / credentials (nightly)
filterwarnings =
    error::pytest.PytestUnknownMarkWarning
```
`e2e`/`external` déclarés mais pas encore utilisés (forward-compat).

**Gotcha pytest 9.0.3 (vérifié le 2026-07-09).** Sous cette version, `--strict-markers` placé
dans `addopts` **ne mord pas** (un marqueur inconnu ne produit qu'un `PytestUnknownMarkWarning`,
exit 0) — reproduit même en isolation totale, hors conftest. Seul `--strict-markers` en **CLI**
convertit en erreur. Pour tenir le cliquet « hygiène marqueurs » depuis la config (source unique,
toutes invocations : CI, Makefile, local, futurs hooks), on escalade le warning spécifique via
`filterwarnings = error::pytest.PytestUnknownMarkWarning` — ce qui, lui, s'applique bien depuis
l'ini. On conserve `--strict-markers` en addopts (inoffensif, auto-documentant, redeviendra utile
si la régression pytest est corrigée). L'escalade est ciblée sur cette seule classe de warning :
la suite complète reste verte (1401 passed vérifié).

### `pyproject.toml`
- Supprimer le bloc `[tool.pytest.ini_options]` dupliqué.
- Ajouter `pytest-cov` au groupe `dev`.
- Ajouter :
```toml
[tool.coverage.run]
branch = true
source = ["web", "lib"]

[tool.coverage.report]
precision = 2
```

### `.github/workflows/ci.yml` (job `test`)
Retirer le `--with 'pytest-cov>=7'` (dép dev désormais), garder `-m "not integration"`, ajouter le gate :
```
uv run pytest tests/ -q --tb=short -m "not integration" \
  --cov --cov-branch --cov-fail-under=74.90 --cov-report=term-missing:skip-covered
```

### `Makefile`
Répercuter `--cov-branch --cov-fail-under=74.90` dans la cible `test` (ou nouvelle cible `test-cov`
appelée par `ci`) pour que `make ci` tienne la même loi en local.

## Définition de « fait » (tests négatifs à exécuter avant conclusion)

1. Baisser artificiellement la couverture (supprimer un test) → `make ci` **rouge** sur `--cov-fail-under`.
2. Marqueur mal orthographié (`@pytest.mark.integraton`) → **collecte rouge** (`--strict-markers`).
3. Suite complète toujours **verte** au niveau baseline (74,90 %).

## Hors périmètre (phases ultérieures)

Détecteurs de slop (Phase 3), hooks Claude Code (Phase 4), unit hermétique + découpe CI (Phase 5),
typage/contrats (Phase 6). Ici : uniquement le sol, gelé.

## Zone critique

`web/models.py`, `alembic/`, `web/runner.py`, etc. : **non touchés**. `.github/workflows/ci.yml`
n'est pas listé en zone critique mais touche l'infra de vérification → à signaler dans la PR.
