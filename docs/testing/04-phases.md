# Les phases : pourquoi, comment, mise en place

Chaque phase est décrite par : le **problème** qu'elle résout, la **garantie déterministe** qu'elle ajoute, le **cliquet** qu'elle pose, et la **mise en place** concrète (artefacts à produire).

L'**ordre d'exécution réel** (dépendances, parallélisme, couplages) est dans [`03-roadmap.md`](03-roadmap.md) — à lire avant de se lancer. Les numéros ci-dessous suivent un ordre de lecture.

> État de départ (vérifié) : ~80 fichiers de tests à plat dans `tests/` ; `pytest.ini` avec un seul marqueur `integration` (définition obsolète : « needs Matomo credentials ») ; bloc `markers` dupliqué dans `pyproject.toml` ; `conftest.py` crée la base **à l'import** (l'unit n'est pas hermétique) ; la CI **mesure déjà** la couverture (`--cov=web --cov=lib`) sans la bloquer ; **aucun** vérificateur de types ; **aucun** usage de Pydantic dans `web/`/`lib/`.

---

## Phase 1 — Geler le plancher + hygiène de config

- **Problème** : on ne bloque rien sur la couverture, alors qu'on la mesure déjà ; et la config des marqueurs est dupliquée/obsolète, donc la frontière unit/integration n'est pas fiable.
- **Garantie déterministe** : la couverture globale ne peut plus descendre sous une baseline ; un marqueur mal orthographié casse la CI.
- **Cliquet** : premier cran de plancher (couverture globale, **en branches**), monotone. Premier cran de périmètre (les marqueurs déclarés sont les seuls autorisés).
- **Conversion** : « on devrait avoir des tests » → « la CI rougit si la couverture baisse ».

**Mise en place :**

`pytest.ini` (source unique de vérité ; supprimer le bloc `markers` dupliqué de `pyproject.toml`) :

```ini
[pytest]
testpaths = tests
addopts = --strict-markers --strict-config
markers =
    integration: a besoin de Postgres + Redis (TestClient, fakeredis)
    e2e: parcours complet en process (runner + Redis + SSE, agent faké)
    external: vrais services externes / credentials (nightly)
```

CI (job de test) — geler le chiffre **mesuré** (décision : branches dès maintenant) :

```
pytest -m "not external" --cov=web --cov=lib --cov-branch \
       --cov-fail-under=<baseline mesurée> --cov-report=term-missing
```

Ajouter `pytest-cov` aux dépendances dev (la CI l'injecte aujourd'hui via `--with`).

> Décision à figer ici : **branches, pas lignes** (cf. couplage n°2 de la roadmap).

---

## Phase 2 — Couverture du code modifié

- **Problème** : le plancher global regarde la moyenne ; il laisse passer du code neuf non testé tant que la moyenne ne bouge pas.
- **Garantie déterministe** : toute ligne ajoutée/modifiée dans une PR doit être exercée, à seuil élevé, indépendamment de la dette legacy.
- **Cliquet** : le cliquet de « chaque modif a un test », appliqué au diff. Chaque PR pousse vers le haut.
- **Conversion** : la règle `.claude/rules` « chaque modification a un test » passe de requête à l'agent à **loi du merge**.

**Mise en place :**

```
pytest -m "not external" --cov=web --cov=lib --cov-branch --cov-report=xml
diff-cover coverage.xml --compare-branch=origin/main --fail-under=90
```

Job CI dédié (ou step), bloquant. Le seuil (`90`) est un plancher : il ne descend jamais.

---

## Phase 3 — Détecteurs de tests creux

- **Problème** : la couverture prouve qu'une ligne s'exécute, pas qu'elle est vérifiée. Un test sans assertion passe la couverture.
- **Garantie déterministe** : un test manifestement creux fait échouer le lint.
- **Cliquet** : relève le plancher de « test présent » à « test non trivialement creux ».
- **Conversion** : une partie de « le test vérifie vraiment », jusqu'ici jugement humain, devient déterministe.

**Mise en place :**

Règles de lint toutes faites (config ruff) :

```toml
[tool.ruff.lint]
extend-select = ["PT", "B011"]   # flake8-pytest-style + assert-False

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]            # assert autorisé dans les tests
```

Contrôle maison `scripts/check_test_quality.py` (~40 lignes, analyse AST), branché dans `make lint` et en pre-commit, qui rejette dans `tests/` :
- un `def test_*` **sans aucune assertion** ;
- une assertion **tautologique** (constante, ou comparaison dont les deux côtés sont identiques) ;
- un test qui **mocke un symbole du module qu'il couvre** (cible de `mocker.patch` appartenant au module sous test).

---

## Phase 4 — Hooks Claude Code (fail fast)

- **Problème** : tout ce qui précède bloque au merge, donc tard ; l'agent découvre les violations en fin de course.
- **Garantie déterministe** : les mêmes lois s'appliquent *pendant* que l'agent code.
- **Cliquet (temporel)** : ne relève pas le plancher (la CI le tient déjà) mais **avance le moment où il mord** — du merge vers la frappe.
- **Conversion** : « la CI le rattrapera » → « l'agent ne peut pas avancer en violation ».

**Mise en place** (`.claude/settings.json`) :

- **PostToolUse** sur `Edit|Write` de `.py` → `ruff check` + `ruff format --check` du fichier édité ; échec renvoyé sur stderr (exit ≠ 2 : nudge, l'agent itère).
- **Stop** → lance la suite unit + le contrôle de traçabilité code → test sur le diff de session ; **bloque** (`{"decision":"block","reason":…}`) si rouge ou si un fichier source modifié n'a pas de test correspondant.
- **PreToolUse** → étendre la garde existante (déjà active en prod sur `data/`) aux zones critiques de `.claude/rules/zones-critiques.md` (`web/models.py`, `alembic/`, …) : `exit 2` + raison sur stderr.

> Rappel technique : seul `exit 2` bloque (et la sortie JSON est ignorée dans ce cas — utiliser stderr) ; sur `PostToolUse` un `exit 2` ne bloque pas l'édition (déjà faite), il ne fait que renvoyer le message à l'agent. Le hook `Stop` doit converger (au-delà de ~8 blocages consécutifs, Claude Code passe outre).

---

## Phase 5 — Unit hermétique + découpe CI

- **Problème** : la base est créée à l'import → impossible de prouver qu'un « unit » tourne sans service. La boucle locale est lente (tout exige Postgres).
- **Garantie déterministe** : « tout test non marqué tourne sans service » devient une propriété vérifiée par un job CI **sans Postgres**.
- **Cliquet (périmètre)** : la frontière unit/integration devient réelle et vérifiable, plus déclarative.
- **Conversion** : « ce test est unitaire » (affirmation) → « la CI sans base le prouve ».

**Mise en place :**

- Rendre `conftest.py` **lazy** : retirer la création de base au niveau module, la déplacer dans une fixture dont ne dépendent que les fixtures DB (`app`/`client`). *Chantier transverse reconnu* : la création de schéma est `autouse` session-scoped et de nombreux fichiers importent `web.*` ; le découplage n'est pas un simple déplacement de ligne.
- Découper la CI : job **unit** (`-m "not integration and not e2e and not external"`, sans services) + job **integration** (`-m "integration or e2e"`, avec Postgres + Redis).
- **Couplage n°1 (cf. roadmap)** : chaque job ne couvre qu'une partie du code → **fusionner la couverture des deux jobs** (`coverage combine`) avant d'appliquer `--cov-fail-under` et `diff-cover`, dans la même PR. Sinon le plancher de la phase 1 mesure un bout et casse.
- Cibles `Makefile` : `test-unit` (zéro service), `test` (périmètre PR), `test-cov`.

---

## Phase 6 — Fondation contrats : vérificateur de types *(track parallèle)*

- **Problème** : aucune couche statique ; un rename ou une mauvaise forme n'est attrapé par rien avant l'exécution. Les tests portent le travail d'un compilateur absent.
- **Garantie déterministe** : une signature/forme fausse casse au build, pas à l'exécution.
- **Cliquet (périmètre)** : chaque module passé en strict ne peut plus régresser ; la surface typée ne fait que croître.
- **Conversion** : « rendre les états illégaux non-représentables » — on ne *teste* plus qu'une signature est respectée, on rend *impossible* de la violer.

> Indépendant des phases 1–5 : peut démarrer **dès le jour 1**, en parallèle.

**Mise en place :**

- Ajouter mypy (ou pyright) aux deps dev + un job CI + une cible `make typecheck`.
- Démarrer **strict sur la façade** (`lib/query.py`, `web/config.py`) ; le reste en mode permissif.
- Élargir au cliquet : chaque module basculé en strict est ajouté à une liste qui ne fait que grandir (le périmètre strict ne régresse jamais).
- Plus tard : **Pydantic aux frontières externes** (réponses Matomo/Metabase, payloads `/api/query`, `dashboard_storage`) — parser en schéma, échouer à la frontière. C'est l'équivalent de Zod.

---

## Phase 7 — Rangement en miroir + fakes + factories *(repoussable)*

- **Problème** : 80 fichiers à plat, mock S3 fragile, pas de traçabilité code → test déterministe, liste de `TRUNCATE` en dur. À mesure que l'agent ajoute, ça se dégrade.
- **Garantie déterministe** : pour tout module, son test est à un emplacement mécaniquement prévisible ; une nouvelle table ne peut plus fuir entre tests.
- **Cliquet (périmètre)** : convention de localisation + isolation auto-maintenue.
- **Conversion** : « on sait à peu près où sont les tests » → « la convention est déterministe et l'isolation s'auto-maintient ».

> La plus repoussable : rien avant ne l'exige, rien après n'en dépend strictement.

**Mise en place :**

- Arbo **miroir léger** : `tests/web/`, `tests/lib/`, `tests/cron/`, `tests/skills/` mirrorent le code, flat à l'intérieur ; un `conftest.py` racine unique ; `tests/factories.py` (fonctions `create_*(session, …)`, pas de `factory_boy`) ; les tests sans module source (hooks `.claude/`) restent à la racine de `tests/`.
- `respx` / `httpx.MockTransport` pour Matomo/Metabase/Notion/S3 (interception au niveau HTTP), en remplacement du patch des attributs internes du client S3.
- `truncate_all_tables()` : **dériver la liste de `Base.metadata.sorted_tables`** au lieu de l'énumérer en dur.
- Mettre à jour les `per-file-ignores` à chemins en dur lors des déplacements.

---

## Phase 8 — Profondeur : mutation, évals, justesse des données

- **Problème** : trois trous que rien n'a fermé — un test peut couvrir sans *mordre* (frontières), la qualité des réponses LLM n'est pas évaluée, et la justesse des chiffres n'est pas vérifiée.
- **Garantie déterministe** : on mesure la force réelle des tests (mutation) et on assert la justesse des données ; les évals, non déterministes, posent une **tendance** sans bloquer.
- **Cliquet** : score de mutation sur modules critiques qu'on décide de ne pas laisser baisser ; chaque frontière validée et chaque golden dataset est un acquis.
- **Conversion** : on ferme la *force* des tests et la justesse côté **données** et **frontières** — ce qu'un « tout est vert » peut encore cacher.

**Mise en place :**

- **Mutation** (`mutmut`) en **nightly**, sur le diff / modules critiques (`web/runner.py`, `web/uploads.py`, `lib/query.py`, clients API). Produit un rapport des mutants survivants ; **jamais en gate**.
- **Évals** dans `evals/` (hors `tests/`), via `promptfoo` : ~20 cas représentatifs (dont l'ambiguïté RPE vs autometa_tables_db, hors-périmètre), assertions exactes (bon outil/bonne source/bonnes tables) + juge LLM (grille explicite, option « je ne sais pas »), seuil sur la moyenne de N runs. Déclenché en nightly si le diff touche `web/agents/**`, `knowledge/**`, la config des sources. **Non bloquant.**
- **Circuit déterministe LLM** (sur la PR) : transcripts enregistrés (`.jsonl`) rejoués, subprocess faké (`pytest-subprocess`), snapshot du *format* du prompt et des events (`syrupy`, jamais auto-update en CI).
- **Justesse des données** : golden datasets + tests d'invariants (sommes, non-négativité, cohérence détail/agrégat, unicité) + cohérence inter-sources.

---

## Récapitulatif

| Phase | Pose quoi | Bloque | Type de cliquet |
|---|---|---|---|
| 1 | Plancher couverture (branches) + hygiène marqueurs | merge | plancher + périmètre |
| 2 | Couverture du code modifié | merge | plancher (sur le diff) |
| 3 | Détecteurs de tests creux | commit / merge | plancher (qualité) |
| 4 | Hooks (fail fast in-loop) | in-loop | temporel |
| 5 | Unit hermétique + découpe CI | (vérif) | périmètre |
| 6 | Contrats : types graduel *(parallèle)* | build | périmètre |
| 7 | Rangement miroir + fakes + factories | — | périmètre |
| 8 | Mutation + évals + justesse données | nightly (non bloquant) | plancher (force) |
