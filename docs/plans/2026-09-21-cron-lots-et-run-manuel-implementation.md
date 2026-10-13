# Lots de cron et run manuel — plan d'implémentation

> **Pour les agents :** exécuter tâche par tâche via `superpowers:subagent-driven-development` ou
> `superpowers:executing-plans`. Les étapes sont des cases à cocher.

**But :** supprimer le lot fourre-tout, borner la durée d'un lot, et sortir le run manuel du process web.

**Architecture :** cinq lots nommés, chacun une ligne de `cron.json` donc un conteneur Scalingo. Un
budget facultatif par lot, vérifié entre deux tâches. Le run manuel devient un conteneur one-off
demandé à l'API Scalingo au lieu d'un sous-processus dans le handler HTTP.

**Pile :** Python 3.14, FastAPI, SQLAlchemy 2.0, httpx, pytest + pytest-mock.

**Spec :** `docs/plans/2026-09-21-cron-lots-et-run-manuel.md`

## Contraintes globales

- **Aucun commit.** `.claude/rules/code.md` interdit de commiter ou pousser sans demande explicite.
  Là où le gabarit du skill prévoit un commit, faire tourner `make lint` et les tests concernés.
- TDD strict : test rouge vu échouer, puis implémentation minimale, puis vert.
- pytest uniquement, mocks via le fixture `mocker` de pytest-mock, `parametrize` dès qu'une même
  règle est vérifiée avec des entrées différentes.
- Toute lecture d'environnement passe par `web/config.py`. Tout appel HTTP en `httpx` avec `timeout=`.
- Jamais de f-string dans un `logger.*()`.
- `tests/test_cron.py` et `tests/test_cron_routes.py` sont marqués `integration` : ils exigent
  Postgres (`POSTGRES_PORT=5433 docker compose up -d --wait db redis`, puis
  `DATABASE_URL=postgresql://autometa:autometa@localhost:5433/autometa`). Les tests hermétiques vont
  dans `tests/test_cron_runner.py`.

---

### Tâche 1 : des lots explicites, plus de fourre-tout

**Fichiers :**
- Modifier : `web/cron.py` (`get_batch`, `discover_from_dir`, `discover_from_s3`, `discover_publications`, `run_all`, `main`)
- Modifier : `cron/{check-s3-backups,cleanup-dashboards,facade-audit,refresh-rpe,slack-feedback,suggest-tags,sync-connectors,sync-tags}/CRON.md`
- Modifier : `cron/sync-sites/CRON.md`, `cron/sync-inventory/CRON.md`, `cron.json`
- Test : `tests/test_cron_runner.py`, `tests/test_cron.py`

**Interfaces :**
- Produit : `DASHBOARD_BATCH = "tableaux"` ; `get_batch(meta) -> str | None` ; `discover_from_dir`
  lève `ValueError` si une tâche ne déclare pas de batch ; `run_all(dry_run=False, *, batch)`.

- [ ] **Étape 1 : écrire les tests rouges**

```python
# tests/test_cron_runner.py
def test_a_system_task_without_a_declared_batch_fails_discovery(tmp_path):
    (tmp_path / "sans-batch").mkdir()
    (tmp_path / "sans-batch" / "cron.py").write_text("print('x')")
    (tmp_path / "sans-batch" / "CRON.md").write_text("---\ntitle: Sans batch\n---\n")

    with pytest.raises(ValueError, match="sans-batch"):
        cron.discover_from_dir(tmp_path, "CRON.md", "system")


def test_dashboards_and_publications_land_in_the_dashboard_batch(mocker):
    mocker.patch.object(cron.config, "S3_BUCKET", "bucket")
    session = mocker.MagicMock()
    session.execute.return_value.all.return_value = [("tdb1", "T1", True, 300, "0 6 * * *")]
    mocker.patch.object(cron, "get_db").return_value.__enter__.return_value = session
    mocker.patch.object(cron.s3.interactive, "list_files", return_value=[{"path": "tdb1/cron.py"}])

    assert [task["batch"] for task in cron.discover_from_s3()] == [cron.DASHBOARD_BATCH]
```

- [ ] **Étape 2 : les voir échouer**

`DATABASE_URL= REDIS_URL= uv run --frozen pytest -q tests/test_cron_runner.py -k "without_a_declared_batch or dashboard_batch"`
Attendu : `AttributeError: DASHBOARD_BATCH` pour le second, aucune exception levée pour le premier.

- [ ] **Étape 3 : implémenter**

```python
# web/cron.py — remplace DEFAULT_BATCH
DASHBOARD_BATCH = "tableaux"


def get_batch(meta: dict) -> str | None:
    """Le lot déclaré par la tâche. Chaque lot est une ligne de cron.json, donc un conteneur."""
    return meta.get("batch", "").strip().lower() or None
```

Dans `discover_from_dir`, après `meta = parse_frontmatter(folder / md_name)` :

```python
        batch = get_batch(meta)
        if batch is None:
            # Why: un lot fourre-tout absorbait toute tâche muette, tableaux de bord compris, et
            # personne ne voyait la chaîne grandir. Un lot non déclaré est désormais une erreur.
            raise ValueError(f"cron {folder.name}: aucun batch déclaré dans {md_name}")
```

et `"batch": batch` dans le dict. Dans `discover_from_s3` et `discover_publications`, remplacer
`"batch": DEFAULT_BATCH` par `"batch": DASHBOARD_BATCH`. Dans `run_all`, `batch` devient un
paramètre nommé obligatoire (`def run_all(dry_run: bool = False, *, batch: str)`), et dans `main`
l'argument `--batch` devient `required=True` sans valeur par défaut.

- [ ] **Étape 4 : déclarer les lots dans les huit `CRON.md`**

Ajouter `batch: systeme` au front-matter de `check-s3-backups`, `cleanup-dashboards`,
`facade-audit`, `refresh-rpe`, `slack-feedback`, `suggest-tags`, `sync-connectors`, `sync-tags`.
Remplacer `batch: matomo` et `batch: metabase` par `batch: externes` dans `sync-sites` et
`sync-inventory` ; compléter leur texte : les deux partagent désormais la ligne de 02:00 et
s'enchaînent, ce qui respecte l'étalement décidé en `9bb8255` (ne pas empiler Matomo et Metabase
sur la fenêtre de 06:00).

- [ ] **Étape 5 : réécrire `cron.json`**

```json
{
  "jobs": [
    { "command": "0 2 * * * python -m web.cron --batch externes" },
    { "command": "0 4 * * * python -m web.cron --batch grist" },
    { "command": "0 6 * * * python -m web.cron --batch systeme" },
    { "command": "0 6 * * * python -m web.cron --batch tableaux" },
    { "command": "0 6 * * * python -m web.cron --batch xl", "size": "XL" }
  ]
}
```

- [ ] **Étape 6 : réparer les tests existants qui encodent l'ancien défaut**

`tests/test_cron.py::test_get_batch_defaults_and_normalises` attend `"default"` pour un
front-matter vide. Le remplacer par :

```python
@pytest.mark.parametrize(
    ("frontmatter", "expected"),
    [("---\nbatch: xl\n---\n", "xl"), ("---\nbatch: XL\n---\n", "xl"), ("---\n---\n", None)],
)
def test_get_batch_normalises_and_reports_absence(tmp_path, frontmatter, expected):
    p = tmp_path / "CRON.md"
    p.write_text(frontmatter)
    assert get_batch(parse_frontmatter(p)) == expected
```

Les fabriques `_task(...)` des tests qui passent `batch="default"` deviennent `batch="systeme"`.

- [ ] **Étape 7 : vérifier**

`DATABASE_URL= REDIS_URL= uv run --frozen pytest -q tests/test_cron_runner.py` puis `make lint`.
Attendu : tout vert, y compris les deux tests de cohérence déjà en place
(`test_every_declared_batch_has_a_line_in_cron_json`, `test_the_sync_tasks_run_through_the_runner_in_their_own_batch`,
dont les attentes de batch passent à `externes`).

---

### Tâche 2 : budget de lot

**Fichiers :**
- Modifier : `web/cron.py` (`run_all`, `main`), `cron.json`
- Test : `tests/test_cron_runner.py`

**Interfaces :**
- Consomme : `run_all(dry_run=False, *, batch)` de la tâche 1.
- Produit : `run_all(dry_run=False, *, batch, budget=None)` ; statut `"skipped"` dans `cron_runs`.

- [ ] **Étape 1 : écrire le test rouge**

```python
def test_a_batch_over_its_budget_stops_launching_and_says_which_tasks_it_dropped(mocker):
    tasks = [make_task("a", source=None), make_task("b", source=None), make_task("c", source=None)]
    mocker.patch.object(cron, "discover_cron_tasks", return_value=tasks)
    mocker.patch.object(cron, "is_due", return_value=True)
    # Why: la première tâche consomme tout le budget ; les deux suivantes ne doivent pas partir.
    mocker.patch.object(cron.time, "monotonic", side_effect=[0, 0, 99, 99, 99])
    execute = mocker.patch.object(
        cron, "execute_task", return_value={"slug": "a", "status": "success", "duration_ms": 1, "output": ""}
    )
    record_run = mocker.patch.object(cron, "record_run")
    notify = mocker.patch.object(cron.alerts, "notify_alert_channel")

    cron.run_all(batch="systeme", budget=10)

    assert execute.call_count == 1
    assert [call.args[0]["slug"] for call in record_run.call_args_list] == ["b", "c"]
    assert {call.args[0]["status"] for call in record_run.call_args_list} == {"skipped"}
    notify.assert_called_once()
```

- [ ] **Étape 2 : le voir échouer**

`DATABASE_URL= REDIS_URL= uv run --frozen pytest -q tests/test_cron_runner.py -k over_its_budget`
Attendu : `TypeError: run_all() got an unexpected keyword argument 'budget'`.

- [ ] **Étape 3 : implémenter dans `run_all`**

Avant la boucle : `started = time.monotonic()` et `dropped = []`. Au début de chaque itération,
après les filtres d'éligibilité (`batch`, `enabled`, `is_due`) et avant `execute_task` :

```python
        if budget and time.monotonic() - started >= budget:
            dropped.append(task["slug"])
            now = utcnow()
            record_run(
                {
                    "slug": task["slug"],
                    "status": "skipped",
                    "output": f"Lot {batch} au-delà de son budget de {budget}s",
                    "duration_ms": 0,
                    "started_at": now,
                    "finished_at": now,
                },
                "scheduled",
            )
            continue
```

Après la boucle :

```python
    if dropped:
        logger.warning("cron : lot %s amputé de %d tâche(s)", sanitize_for_log(batch), len(dropped))
        alerts.notify_alert_channel(
            f":hourglass: *Lot `{batch}` au-delà de son budget de {budget}s* — "
            f"{len(dropped)} tâche(s) non exécutée(s) : " + ", ".join(f"`{slug}`" for slug in dropped)
        )
```

Dans `main`, ajouter `parser.add_argument("--budget", type=int, help="Durée maximale du lot, en secondes")`
et passer `budget=args.budget` à `run_all`.

- [ ] **Étape 4 : vérifier le vert, puis ajouter le cas sans budget**

```python
def test_a_batch_without_a_budget_runs_everything(mocker):
    tasks = [make_task("a", source=None), make_task("b", source=None)]
    mocker.patch.object(cron, "discover_cron_tasks", return_value=tasks)
    mocker.patch.object(cron, "is_due", return_value=True)
    execute = mocker.patch.object(
        cron, "execute_task", return_value={"slug": "x", "status": "success", "duration_ms": 1, "output": ""}
    )

    cron.run_all(batch="systeme")

    assert execute.call_count == 2
```

- [ ] **Étape 5 : déclarer le budget du lot des tableaux de bord**

Dans `cron.json`, la ligne `tableaux` devient
`{ "command": "0 6 * * * python -m web.cron --batch tableaux --budget 1500" }`. C'est le seul lot
dont la taille n'est pas bornée par le dépôt.

- [ ] **Étape 6 : vérifier**

`DATABASE_URL= REDIS_URL= uv run --frozen pytest -q tests/test_cron_runner.py` puis `make lint`.

---

### Tâche 3 : client Scalingo

**Fichiers :**
- Créer : `web/scalingo.py`
- Modifier : `web/config.py`, `.env.example`
- Test : `tests/test_scalingo.py`

**Interfaces :**
- Produit : `web/scalingo.py` expose `ScalingoError`, `is_configured() -> bool`,
  `start_one_off(command: str) -> str` (renvoie l'identifiant du conteneur).
- Produit : `config.SCALINGO_API_TOKEN`, `config.SCALINGO_APP_NAME`, `config.SCALINGO_API_URL`.

- [ ] **Étape 1 : écrire les tests rouges**

```python
"""Client Scalingo — lancement d'un conteneur one-off."""

import httpx
import pytest

from web import scalingo


@pytest.fixture
def configured(mocker):
    mocker.patch.object(scalingo.config, "SCALINGO_API_TOKEN", "tk-secret")
    mocker.patch.object(scalingo.config, "SCALINGO_APP_NAME", "matometa")
    mocker.patch.object(scalingo.config, "SCALINGO_API_URL", "https://api.osc-fr1.scalingo.com")


def test_is_configured_requires_both_the_token_and_the_app(mocker):
    mocker.patch.object(scalingo.config, "SCALINGO_API_TOKEN", "tk-secret")
    mocker.patch.object(scalingo.config, "SCALINGO_APP_NAME", "")

    assert scalingo.is_configured() is False


def test_start_one_off_exchanges_the_token_then_returns_the_container_id(configured, mocker):
    post = mocker.patch.object(
        httpx,
        "post",
        side_effect=[
            httpx.Response(200, json={"token": "bearer-xyz"}, request=httpx.Request("POST", "https://auth")),
            httpx.Response(
                200, json={"container": {"id": "ctr-42"}}, request=httpx.Request("POST", "https://api")
            ),
        ],
    )

    assert scalingo.start_one_off("python -m web.cron --app tdb1") == "ctr-42"
    assert post.call_args_list[1].kwargs["headers"]["Authorization"] == "Bearer bearer-xyz"
    assert post.call_args_list[1].kwargs["json"]["command"] == "python -m web.cron --app tdb1"
    assert all(call.kwargs["timeout"] for call in post.call_args_list)


@pytest.mark.parametrize(
    "failure",
    [
        httpx.Response(401, json={"error": "invalid"}, request=httpx.Request("POST", "https://auth")),
        httpx.ConnectError("injoignable"),
    ],
    ids=["refus", "reseau"],
)
def test_start_one_off_raises_a_scalingo_error_when_the_api_refuses_or_is_unreachable(configured, mocker, failure):
    mocker.patch.object(httpx, "post", side_effect=[failure] if isinstance(failure, Exception) else [failure])

    with pytest.raises(scalingo.ScalingoError):
        scalingo.start_one_off("python -m web.cron --app tdb1")
```

- [ ] **Étape 2 : les voir échouer**

`DATABASE_URL= REDIS_URL= uv run --frozen pytest -q tests/test_scalingo.py`
Attendu : `ModuleNotFoundError: No module named 'web.scalingo'`.

- [ ] **Étape 3 : implémenter la configuration**

Dans `web/config.py`, à côté des autres jetons :

```python
# Scalingo — lancement d'un conteneur one-off pour les runs manuels de cron.
SCALINGO_API_TOKEN = os.getenv("SCALINGO_API_TOKEN", "")
SCALINGO_APP_NAME = os.getenv("SCALINGO_APP_NAME", "")
SCALINGO_API_URL = os.getenv("SCALINGO_API_URL", "https://api.osc-fr1.scalingo.com")
```

Et les trois lignes commentées correspondantes dans `.env.example`.

- [ ] **Étape 4 : implémenter le client**

```python
"""Client Scalingo — juste assez pour lancer un conteneur one-off."""

import logging

import httpx

from . import config

logger = logging.getLogger(__name__)

TOKEN_EXCHANGE_URL = "https://auth.scalingo.com/v1/tokens/exchange"


class ScalingoError(RuntimeError):
    """L'API Scalingo a refusé ou n'a pas répondu."""


def is_configured() -> bool:
    return bool(config.SCALINGO_API_TOKEN and config.SCALINGO_APP_NAME)


def start_one_off(command: str) -> str:
    """Lance `command` dans un conteneur éphémère et renvoie son identifiant."""
    try:
        exchange = httpx.post(TOKEN_EXCHANGE_URL, auth=("", config.SCALINGO_API_TOKEN), timeout=10)
        exchange.raise_for_status()
        bearer = exchange.json()["token"]
        run = httpx.post(
            f"{config.SCALINGO_API_URL}/v1/apps/{config.SCALINGO_APP_NAME}/run",
            headers={"Authorization": f"Bearer {bearer}"},
            json={"command": command, "detached": True},
            timeout=20,
        )
        run.raise_for_status()
        return run.json()["container"]["id"]
    except (httpx.HTTPError, KeyError) as e:
        raise ScalingoError(f"lancement du conteneur refusé : {e}") from e
```

- [ ] **Étape 5 : vérifier**

`DATABASE_URL= REDIS_URL= uv run --frozen pytest -q tests/test_scalingo.py` puis `make lint`.
Attendu : vert, et `scripts/check_http_timeouts.py` (lancé par `make lint`) silencieux.

---

### Tâche 4 : l'essaimage des publications part dans le conteneur

**Fichiers :**
- Modifier : `web/cron.py` (nouvelle fonction + `main`)
- Test : `tests/test_cron_runner.py`

**Interfaces :**
- Produit : `run_task_and_publications(slug: str, trigger: str = "manual") -> list[dict]`.

- [ ] **Étape 1 : écrire le test rouge**

```python
def test_a_manual_run_of_a_dashboard_also_refreshes_its_publications(mocker):
    mocker.patch.object(cron, "find_task", return_value=make_task("tdb1"))
    mocker.patch.object(
        cron, "list_publications", return_value=[{"publication_id": "pub1", "snapshot_has_cron": True, "refresh_paused_at": None}]
    )
    run = mocker.patch.object(cron, "run_cron_task", return_value={"slug": "x", "status": "success", "duration_ms": 1})

    results = cron.run_task_and_publications("tdb1")

    assert [call.args[0] for call in run.call_args_list] == ["tdb1", "tdb1-pub1"]
    assert len(results) == 2
```

- [ ] **Étape 2 : le voir échouer**

`DATABASE_URL= REDIS_URL= uv run --frozen pytest -q tests/test_cron_runner.py -k also_refreshes`
Attendu : `AttributeError: module 'web.cron' has no attribute 'run_task_and_publications'`.

- [ ] **Étape 3 : implémenter**

Dans `web/cron.py`, importer `from .publications import list_publications` en tête de module, puis :

```python
def run_task_and_publications(slug: str, trigger: str = "manual") -> list[dict]:
    """Rejoue une tâche puis, si c'est un tableau de bord, chacune de ses publications actives."""
    task = find_task(slug)
    results = [run_cron_task(slug, trigger)]
    if task and task.get("source") == "s3":
        for pub in list_publications(slug, active_only=True):
            if pub.get("snapshot_has_cron") and not pub.get("refresh_paused_at"):
                results.append(run_cron_task(f"{slug}-{pub['publication_id']}", trigger))
    return results
```

Dans `main`, la branche `--app` appelle `run_task_and_publications(args.app, trigger="manual")` et
imprime une ligne par résultat.

- [ ] **Étape 4 : vérifier**

`DATABASE_URL= REDIS_URL= uv run --frozen pytest -q tests/test_cron_runner.py` puis `make lint`.
Attention à l'import circulaire : `web/publications.py` n'importe pas `web/cron.py`, donc l'import
en tête de module passe ; si ce n'était pas le cas, la règle `code.md` exigerait un `# Why:` écrit.

---

### Tâche 5 : la route déclenche un conteneur et rend la main

**Fichiers :**
- Modifier : `web/routes/cron.py` (`POST /api/cron/{slug}/run`)
- Modifier : `web/templates/cron.html` (message après déclenchement)
- Test : `tests/test_cron_routes.py`

**Interfaces :**
- Consomme : `scalingo.is_configured()`, `scalingo.start_one_off()` (tâche 3),
  `run_task_and_publications` (tâche 4, exécutée dans le conteneur, pas dans la route).

- [ ] **Étape 1 : écrire les tests rouges**

```python
def test_a_manual_run_is_delegated_to_a_dedicated_container(client, mocker):
    mocker.patch("web.routes.cron.find_task", return_value={"slug": "tdb1", "source": "s3"})
    mocker.patch("web.routes.cron.scalingo.is_configured", return_value=True)
    start = mocker.patch("web.routes.cron.scalingo.start_one_off", return_value="ctr-42")
    execute = mocker.patch("web.routes.cron.run_cron_task")

    response = client.post("/api/cron/tdb1/run")

    assert response.status_code == 202
    assert response.json()["container"] == "ctr-42"
    assert start.call_args.args[0] == "python -m web.cron --app tdb1"
    execute.assert_not_called()


def test_a_manual_run_says_so_when_scalingo_is_not_configured(client, mocker):
    mocker.patch("web.routes.cron.find_task", return_value={"slug": "tdb1", "source": "s3"})
    mocker.patch("web.routes.cron.scalingo.is_configured", return_value=False)

    response = client.post("/api/cron/tdb1/run")

    assert response.status_code == 503
    assert "ligne de commande" in response.json()["error"]


def test_a_manual_run_reports_a_refused_container(client, mocker):
    mocker.patch("web.routes.cron.find_task", return_value={"slug": "tdb1", "source": "s3"})
    mocker.patch("web.routes.cron.scalingo.is_configured", return_value=True)
    mocker.patch("web.routes.cron.scalingo.start_one_off", side_effect=scalingo.ScalingoError("refus"))

    assert client.post("/api/cron/tdb1/run").status_code == 502
```

- [ ] **Étape 2 : les voir échouer**

`POSTGRES_PORT=5433 docker compose up -d --wait db redis` puis
`DATABASE_URL=postgresql://autometa:autometa@localhost:5433/autometa uv run --frozen pytest -q tests/test_cron_routes.py -k manual_run`
Attendu : 200 au lieu de 202, parce que la route exécute encore la tâche elle-même.

- [ ] **Étape 3 : implémenter**

```python
@router.post("/api/cron/{slug}/run", status_code=202)
def run_task(slug: Slug):
    """Déclenche un run manuel dans un conteneur dédié — jamais dans le process web."""
    if not find_task(slug):
        return JSONResponse({"error": "Task not found"}, status_code=404)

    if not scalingo.is_configured():
        return JSONResponse(
            {"error": "Run manuel indisponible ici : lancer `python -m web.cron --app <slug>` en ligne de commande."},
            status_code=503,
        )

    try:
        container = scalingo.start_one_off(f"python -m web.cron --app {slug}")
    except scalingo.ScalingoError as e:
        logger.warning("cron %s : conteneur refusé (%s)", sanitize_for_log(slug), e)
        return JSONResponse({"error": "Scalingo a refusé le lancement"}, status_code=502)

    return {"slug": slug, "status": "queued", "container": container}
```

Retirer l'import de `list_publications` devenu inutile dans la route, et `run_cron_task` s'il n'est
plus utilisé ailleurs dans le fichier.

- [ ] **Étape 4 : adapter l'interface**

Dans `web/templates/cron.html`, le retour du bouton « lancer » affiche désormais « lancé dans un
conteneur dédié — rafraîchir dans quelques instants » au lieu de la sortie de la tâche, puisque
celle-ci n'existe plus au moment de la réponse.

- [ ] **Étape 5 : vérifier**

Tests de route avec Postgres, puis la suite unit, puis `make lint`, puis la suite complète :
`DATABASE_URL=postgresql://autometa:autometa@localhost:5433/autometa uv run --frozen pytest -q tests/ infra/ -m "not external"`.
Éteindre ensuite les conteneurs : `docker compose down`.

---

## Auto-relecture

**Couverture de la spec** — découpe en cinq lots : tâche 1. Disparition du fourre-tout : tâche 1,
étapes 3 et 6. Budget déclaré dans `cron.json` et statut `skipped` : tâche 2. Absence de priorités :
rien à faire, c'est une non-décision assumée. Conteneur one-off et 503 sans jeton : tâches 3 et 5.
Essaimage déplacé : tâche 4. Une seule découverte par clic : tâche 5, étape 3 (`find_task` une fois,
plus de `run_cron_task` dans la route).

**Cohérence des noms** — `DASHBOARD_BATCH`, `get_batch`, `run_all(..., batch=, budget=)`,
`is_configured`, `start_one_off`, `ScalingoError`, `run_task_and_publications` sont employés avec la
même signature dans toutes les tâches.

**Point de vigilance non couvert par un test** — la région de l'API Scalingo (`osc-fr1`, déduite des
URL de base de données de production) doit être confirmée au déploiement ; une mauvaise valeur ne se
verra qu'au premier clic en production, sous la forme d'un 502.
