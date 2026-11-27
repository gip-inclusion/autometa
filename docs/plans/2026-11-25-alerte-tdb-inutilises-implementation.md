# Alerte TDB sans visite depuis 60 jours — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chaque matin, un message Slack agrégé liste les TDB non archivés, créés il y a plus de 60 jours, sans aucune visite Matomo sur les 60 derniers jours, avec nom du propriétaire et lien vers la fiche.

**Architecture:** Un module `web/unused_dashboards.py` (fonctions pures + une fonction d'orchestration), appelé par une tâche `cron/alert-unused-dashboards/` du batch `maintenance`. 60 requêtes Matomo `Actions.getPageUrls` en `period=day` (archives précalculées, sans regroupement « Others »), regroupées en un seul appel `API.getBulkRequest` : coût constant quel que soit le nombre de TDB, aucune modification de `lib/`.

**Tech Stack:** Python, `lib.query.execute_matomo_query`, `web.database.store`, `web.alerts.notify_alert_channel`, pytest + pytest-mock.

**Spec:** `docs/plans/2026-11-25-alerte-tdb-inutilises.md`

## Global Constraints

- Matomo : instance `inclusion`, site `224` (Autometa), `caller=CallerType.CRON`, un seul appel `API.getBulkRequest` (timeout 60 s).
- Fenêtre : les 60 jours complets précédant aujourd'hui (J-60 à J-1, UTC).
- Candidat : `is_archived` faux et `created_at <= now - 60 jours`.
- Vu = au moins une ligne Matomo dont le chemin commence par `/interactive/<slug>` ou `/dashboards/<slug>` (2e segment du chemin = slug).
- Aucun tag Slack : nom déduit de l'email (`prenom.nom@…` → « Prenom Nom »), sinon l'email brut.
- Lien : `{config.BASE_URL}/dashboards/<slug>`.
- Aucun envoi si la liste est vide. Aucun envoi et exception si l'appel échoue ou si un jour revient en `{"result": "error"}`.
- Conventions `.claude/rules/code.md` et `tests.md` : pas de commentaire « quoi », docstring une ligne, `mocker`, `parametrize`, aucun service requis (test non marqué).
- Aucun commit sans accord explicite de l'utilisateur.

## Review Focus

- Une journée Matomo regroupe les pages en `/interactive/ - Others` ou `/dashboards/ - Others` : des visites seraient cachées → l'orchestration doit lever plutôt que lister à tort (test dans Task 1).
- Libellés sans slash final, avec sous-page ou query string (`/interactive/x`, `/interactive/x/index.html?onglet=carte`) : comptent pour `x` (test dans Task 1).
- Slug préfixe d'un autre (`rdvi-13` vs `rdvi-13-2`) : une visite de `rdvi-13-2` ne compte pas pour `rdvi-13` (test dans Task 1).
- TDB créé il y a 59 jours sans visite : non listé (test dans Task 1).
- Email sans point (`anonyme@…`) : l'email brut s'affiche (test dans Task 1).
- Réponse groupée réussie mais un jour en `{"result": "error", "message": …}` : exception, aucun envoi (test dans Task 1).

---

### Task 1: Module `web/unused_dashboards.py`

**Files:**
- Create: `web/unused_dashboards.py`
- Test: `tests/test_unused_dashboards.py`

**Interfaces:**
- Consumes: `execute_matomo_query(instance, caller, method, params, timeout) -> QueryResult(success, data, error)` ; `store.list_dashboards() -> list[dict]` (clés `slug`, `title`, `first_author_email`, `created_at`) ; `notify_alert_channel(message: str) -> None`.
- Produces: `report_unused_dashboards() -> None` (utilisé par Task 2).

- [ ] **Step 1: Écrire les tests en échec**

Fonction usine locale `dashboard(slug, days_old=90, email="prenom.nom@inclusion.gouv.fr", title=None) -> dict`.

```python
@pytest.mark.parametrize(("labels", "expected"), [
    (["/interactive/x/"], {"x"}),
    (["/interactive/x"], {"x"}),
    (["/interactive/x/index.html?onglet=carte"], {"x"}),
    (["/dashboards/y/"], {"y"}),
    (["/dashboards/y/ - Others"], {"y"}),
    (["/explorations/abc", "/", "Page URL not defined"], set()),
])
def test_visited_slugs(labels, expected):
    assert visited_slugs([{"label": l} for l in labels]) == expected

@pytest.mark.parametrize("label", ["/interactive/ - Others", "/dashboards/ - Others"])
def test_visited_slugs_refuses_truncated_day(label):
    with pytest.raises(RuntimeError):
        visited_slugs([{"label": label}])

@pytest.mark.parametrize(("email", "expected"), [
    ("prenom.nom@inclusion.gouv.fr", "Prenom Nom"),
    ("jean-marc.dupont@x.fr", "Jean-Marc Dupont"),
    ("anonyme@x.fr", "anonyme@x.fr"),
])
def test_owner_name(email, expected): ...

def test_unused_dashboards_keeps_old_unvisited_sorted_by_title():
    # candidats : "b" (90 j, non vu, titre "Zeta"), "a" (90 j, non vu, titre "Alpha"),
    # "vu" (90 j, vu), "jeune" (59 j, non vu), "rdvi-13" (90 j) avec visited={"rdvi-13-2", "vu"}
    # attendu : slugs ["a", "rdvi-13", "b"] triés par titre

def test_report_posts_one_message(mocker):
    # execute_matomo_query mocké : succès, data = 60 listes [{"label": "/interactive/vu/"}]
    # store.list_dashboards mocké : [dashboard("vu"), dashboard("mort", title="Suivi OKR")]
    # BASE_URL patché à "https://autometa.test"
    # assert execute_matomo_query appelé 1 fois, method="API.getBulkRequest", params urls[0]..urls[59]
    #        contenant chacun "method=Actions.getPageUrls", "idSite=224", "period=day", dates J-1..J-60
    # assert notify_alert_channel appelé une fois ; message contient "Suivi OKR", "Prenom Nom",
    #        "https://autometa.test/dashboards/mort", et pas "vu"

def test_report_silent_when_all_visited(mocker):
    # tous vus → notify_alert_channel non appelé

@pytest.mark.parametrize("result", [
    QueryResult(success=False, data=None, error="timeout"),
    QueryResult(success=True, data=[[]] * 59 + [{"result": "error", "message": "archive"}]),
])
def test_report_raises_and_stays_silent_on_matomo_failure(mocker, result):
    # → RuntimeError, notify_alert_channel non appelé
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `.venv/bin/pytest tests/test_unused_dashboards.py -v`
Expected: FAIL (`ModuleNotFoundError: web.unused_dashboards`)

- [ ] **Step 3: Implémenter `web/unused_dashboards.py`**

- `visited_slugs(rows: list[dict]) -> set[str]` : 2e segment de `label.split("/")` si le 1er est `interactive` ou `dashboards` ; lève `RuntimeError` si le libellé vaut `/interactive/ - Others` ou `/dashboards/ - Others`.
- `owner_name(email: str) -> str` : partie locale découpée sur `.` puis `str.title()` ; l'email brut s'il n'y a pas de point.
- `unused_dashboards(dashboards: list[dict], visited: set[str], now: datetime) -> list[dict]` : filtre `created_at <= now - timedelta(days=60)` et slug hors `visited`, tri par `title`.
- `format_alert(dashboards: list[dict]) -> str` : en-tête `"{n} tableaux de bord sans visite depuis 60 jours — à archiver ? Prévenir les propriétaires."` puis une ligne `• {title} — {owner_name} — {BASE_URL}/dashboards/{slug}` par TDB.
- `report_unused_dashboards() -> None` : un appel `execute_matomo_query("inclusion", CallerType.CRON, "API.getBulkRequest", {f"urls[{i}]": f"method=Actions.getPageUrls&idSite=224&period=day&date={jour}&flat=1&filter_limit=-1"}, timeout=60)` pour les jours J-1..J-60 ; `RuntimeError` avec `result.error` si échec, ou avec le message si un élément est un dict `{"result": "error"}` ; union des `visited_slugs` de chaque liste ; `unused_dashboards(store.list_dashboards(), visited, utcnow())` ; `notify_alert_channel(format_alert(...))` si non vide. Le `224` porte un commentaire court (site Matomo Autometa).

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `.venv/bin/pytest tests/test_unused_dashboards.py -v`
Expected: PASS

### Task 2: Tâche cron `alert-unused-dashboards`

**Files:**
- Create: `cron/alert-unused-dashboards/CRON.md`, `cron/alert-unused-dashboards/cron.py`

**Interfaces:**
- Consumes: `report_unused_dashboards()` (Task 1), `web.cron_task.run`.

- [ ] **Step 1: Créer `CRON.md`**

Front-matter `title: Alerter sur les tableaux de bord sans visite depuis 60 jours`, `schedule: daily`, `timeout: 300`, `batch: maintenance`. Corps : le quoi et le pourquoi en 2-3 lignes (liste quotidienne cumulative jusqu'à archivage, archives Matomo journalières car les plages regroupent la traîne), sans détail d'implémentation.

- [ ] **Step 2: Créer `cron.py`** sur le modèle de `cron/check-s3-backups/cron.py` : docstring une ligne, `run(report_unused_dashboards)`.

- [ ] **Step 3: Vérifier la découverte et la suite**

Run: `.venv/bin/pytest tests/test_cron.py tests/test_unused_dashboards.py -q && make lint && make test`
Expected: PASS ; `discover_from_dir` trouve `alert-unused-dashboards` dans le batch `maintenance`.

- [ ] **Step 4: Preuve réelle (lecture seule)**

Run, avec les identifiants Matomo locaux et `notify_alert_channel` remplacé par `print` : appeler `report_unused_dashboards()` sur une liste de TDB factice ou la base locale.
Expected : un appel Matomo de quelques secondes, aucune `RuntimeError` de troncature, message imprimé cohérent.
