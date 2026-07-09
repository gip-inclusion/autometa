# Phase 1 — Plancher de couverture + hygiène marqueurs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Graver le niveau de couverture actuel (74,90 % en branches) comme plancher CI infranchissable, et rendre la config des marqueurs pytest unique et stricte.

**Architecture:** Deux cliquets déterministes, purement config (aucun code applicatif touché). (1) `--cov-fail-under=74.90` sur la couverture de **branches** dans la CI et `make ci`. (2) `--strict-markers --strict-config` avec une source unique de vérité pour les marqueurs (`pytest.ini`), suppression du bloc dupliqué de `pyproject.toml`.

**Tech Stack:** pytest, pytest-cov, coverage.py (branch mode), uv, GitHub Actions, Make.

## Global Constraints

- Couverture de **branches**, jamais de lignes (figé une seule fois — couplage n°2 de `docs/testing/03-roadmap.md`).
- Plancher = **74.90** avec `precision = 2` (mesuré le 2026-07-09, environnement local ≡ CI). Repli `74` si rouge flaky.
- Le gate garde la sélection **`-m "not integration"`** (e2e/external pas encore posés — runbook §5.4).
- Cliquet **monotone** : un plancher ne descend jamais ; le baisser = revue humaine.
- `uv ... --frozen` en CI → toute nouvelle dép dev **doit** mettre `uv.lock` à jour.
- Mesure locale : `DATABASE_URL=postgresql://autometa:autometa@localhost:5433/autometa` + `REDIS_URL=redis://localhost:6379/0`.
- Commits en anglais, concis. **Ne pas pousser** (l'utilisateur pousse).

## File Structure

- `pytest.ini` — source unique de vérité des marqueurs + `addopts` stricts.
- `pyproject.toml` — retrait du bloc `[tool.pytest.ini_options]` dupliqué ; `pytest-cov` en dev ; config `[tool.coverage.*]`.
- `uv.lock` — régénéré par l'ajout de `pytest-cov`.
- `.github/workflows/ci.yml` — job `test` : gate couverture.
- `Makefile` — cible `test` : mêmes flags, pour que `make ci` tienne la loi en local.

---

### Task 1: Hygiène des marqueurs (config stricte, source unique)

**Files:**
- Modify: `pytest.ini`
- Modify: `pyproject.toml` (supprimer `[tool.pytest.ini_options]`)

**Interfaces:**
- Consumes: rien.
- Produces: 3 marqueurs déclarés (`integration`, `e2e`, `external`) + `--strict-markers --strict-config` actifs pour toute invocation pytest.

- [ ] **Step 1: Réécrire `pytest.ini`**

Remplacer intégralement le contenu par :

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

> **Gotcha pytest 9.0.3 (vérifié)** : `--strict-markers` en `addopts` ne mord pas sous cette
> version (marqueur inconnu → simple warning). C'est `filterwarnings = error::pytest.PytestUnknownMarkWarning`
> qui fait réellement échouer la collecte depuis l'ini. On garde `--strict-markers` (auto-documentant).

- [ ] **Step 2: Supprimer le bloc dupliqué de `pyproject.toml`**

Retirer ces lignes (section morte, `pytest.ini` a la priorité) :

```toml
[tool.pytest.ini_options]
markers = [
    "integration: tests that require external services or credentials",
]
```

- [ ] **Step 3: Vérifier que la collecte reste verte**

Run: `DATABASE_URL=postgresql://autometa:autometa@localhost:5433/autometa REDIS_URL=redis://localhost:6379/0 uv run --frozen pytest tests/ --collect-only -q -m "not integration" 2>&1 | tail -5`
Expected: collecte sans erreur (`~1401 tests collected` / pas de `ERROR`).

- [ ] **Step 4: Test négatif — un marqueur inconnu casse la collecte**

Créer un fichier jetable `tests/test_strict_marker_probe.py` :

```python
import pytest


@pytest.mark.integraton  # faute volontaire
def test_probe():
    assert True
```

Run: `DATABASE_URL=postgresql://autometa:autometa@localhost:5433/autometa REDIS_URL=redis://localhost:6379/0 uv run --frozen pytest tests/test_strict_marker_probe.py --collect-only -q >/dev/null 2>&1; echo "exit=$?"`
Expected: **exit=2** — collecte en erreur `pytest.PytestUnknownMarkWarning: Unknown pytest.mark.integraton` (preuve que `filterwarnings` mord).

- [ ] **Step 4b: Vérifier que la suite complète reste verte (escalade ciblée, sans dégât)**

Run: `DATABASE_URL=postgresql://autometa:autometa@localhost:5433/autometa REDIS_URL=redis://localhost:6379/0 uv run --frozen pytest tests/ -q -m "not integration" 2>&1 | tail -2`
Expected: `1401 passed, 45 deselected` (l'escalade ne touche que `PytestUnknownMarkWarning`).

- [ ] **Step 5: Supprimer le fichier jetable**

```bash
rm tests/test_strict_marker_probe.py
```

- [ ] **Step 6: Commit**

```bash
git add pytest.ini pyproject.toml
git commit -m "test: single strict marker config (integration/e2e/external)"
```

---

### Task 2: Plancher de couverture (branches, 74.90) en CI et en local

**Files:**
- Modify: `pyproject.toml` (deps dev + `[tool.coverage.*]`)
- Modify: `uv.lock` (régénéré)
- Modify: `.github/workflows/ci.yml` (job `test`)
- Modify: `Makefile` (cible `test`)

**Interfaces:**
- Consumes: config stricte de la Task 1.
- Produces: `--cov-fail-under=74.90` sur la couverture de branches, appliqué en CI et par `make ci`.

- [ ] **Step 1: Ajouter `pytest-cov` en dép dev (met à jour `uv.lock`)**

```bash
uv add --dev "pytest-cov>=7"
```
Expected: `pyproject.toml` (groupe `dev`) et `uv.lock` mis à jour ensemble.

- [ ] **Step 2: Ajouter la config couverture à `pyproject.toml`**

Ajouter (après le bloc ruff, dans la zone des outils) :

```toml
[tool.coverage.run]
branch = true
source = ["web", "lib"]

[tool.coverage.report]
precision = 2
```

- [ ] **Step 3: Mettre à jour le job `test` de `.github/workflows/ci.yml`**

Remplacer le step « Unit tests » :

```yaml
      - name: Unit tests
        run: >-
          uv run --with 'pytest-cov>=7' pytest tests/ -q --tb=short -m "not integration"
          --cov=web --cov=lib --cov-report=term-missing:skip-covered
```

par :

```yaml
      - name: Unit tests
        run: >-
          uv run pytest tests/ -q --tb=short -m "not integration"
          --cov --cov-branch --cov-fail-under=74.90 --cov-report=term-missing:skip-covered
```

- [ ] **Step 4: Mettre à jour la cible `test` du `Makefile`**

Remplacer :

```make
test:
	uv run --frozen pytest tests/ -q --tb=short -m "not integration"
```

par :

```make
test:
	uv run --frozen pytest tests/ -q --tb=short -m "not integration" \
		--cov --cov-branch --cov-fail-under=74.90 --cov-report=term-missing:skip-covered
```

- [ ] **Step 5: Test positif — la suite passe au niveau baseline**

Run: `DATABASE_URL=postgresql://autometa:autometa@localhost:5433/autometa REDIS_URL=redis://localhost:6379/0 make test 2>&1 | tail -5`
Expected: **PASS** — `Required test coverage of 74.9% reached.` (ou équivalent) + `1401 passed`.

- [ ] **Step 6: Test négatif — le gate mord si on exige plus haut**

Run: `DATABASE_URL=postgresql://autometa:autometa@localhost:5433/autometa REDIS_URL=redis://localhost:6379/0 uv run --frozen pytest tests/ -q -m "not integration" --cov --cov-branch --cov-fail-under=99 --cov-report= 2>&1 | tail -3`
Expected: **échec** — `Coverage failure: total of 74.90 is less than fail-under=99` (preuve que le plancher bloque une baisse).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock .github/workflows/ci.yml Makefile
git commit -m "test: freeze branch coverage floor at 74.90%"
```

---

## Self-Review

**Spec coverage :**
- Plancher couverture branches 74.90 → Task 2 (steps 2–4). ✅
- Hygiène marqueurs stricte + purge duplicata → Task 1. ✅
- `pytest-cov` en dev + retrait `--with` → Task 2 (steps 1, 3). ✅
- `make ci` tient la loi → Task 2 (step 4). ✅
- Tests négatifs (marqueur + couverture) → Task 1 step 4, Task 2 step 6. ✅
- Branches pas lignes → Global Constraints + Task 2 step 2. ✅

**Placeholder scan :** aucun TBD/TODO ; commandes et contenus complets. ✅

**Type consistency :** N/A (config). Valeur `74.90` et flag `--cov-branch` cohérents partout (CI, Makefile). ✅

**Note zone critique :** `.github/workflows/ci.yml` touche l'infra de vérification → à signaler dans la PR (pas de fichier de zone critique au sens de `.claude/rules/zones-critiques.md`).
