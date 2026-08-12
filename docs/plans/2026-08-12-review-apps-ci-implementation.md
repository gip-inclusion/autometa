# Review apps pilotées par la CI — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lier le cycle de vie des review apps Scalingo à celui des pull requests GitHub, piloté par la CI.

**Architecture:** Un script Python réconcilie l'état des review apps avec l'état des PR via l'API Scalingo — il compare le SHA déployé au `head.sha` de la PR et décide de créer, mettre à jour, ou ne rien faire. Deux workflows l'appellent : un job dans `ci.yml`, conditionné au vert des tests, et un workflow de teardown sur fermeture de PR. La restitution passe par l'API Deployments de GitHub.

**Tech Stack:** Python 3.14, `httpx`, `argparse`, pytest + pytest-mock, GitHub Actions, API Scalingo v1.

Spec de référence : `docs/plans/2026-08-11-review-apps-ci-design.md`.

## Global Constraints

- App parente : `autometa-staging`. Région : `osc-fr1`.
- API Scalingo : `https://api.osc-fr1.scalingo.com/v1`. Échange de token : `https://auth.scalingo.com/v1/tokens/exchange`.
- Secret CI : `SCALINGO_REVIEW_APP_TOKEN`, dans l'Environment GitHub `review-app` (déjà créé).
- HTTP exclusivement en `httpx`, avec un `timeout=` explicite à chaque appel (`.claude/rules/code.md`).
- Aucune lecture de variable d'environnement dans le script : `web/config.py` est le seul endroit autorisé, et il n'est pas importable en CI (il exige `DATABASE_URL` et charge Sentry). Le token arrive donc par **stdin**, jamais par `argv` (visible dans `ps`) ni par `os.environ`.
- Imports groupés en tête de module, pas d'imports différés.
- Pas de commentaire décrivant ce que fait le code. Docstrings d'une ligne maximum.
- Pas de préfixe `_` par habitude : le réserver aux symboles volontairement privés.
- `ruff` : `line-length = 120`, `target-version = "py314"`.
- Couverture : `scripts/` est dans `[tool.coverage.run] source`, et `diff-cover` impose **90 %** sur les lignes modifiées.
- `scripts/` n'est pas un package Python. Les tests le chargent par `importlib.util.spec_from_file_location`, comme `tests/test_check_test_quality.py`.
- Actions GitHub épinglées par SHA : `actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd` (v6.0.2), `astral-sh/setup-uv@37802adc94f370d6bfd71619e3f0bf239e1f3b78` (v7.6.0).
- Messages de commit en anglais, concis. **Ne jamais exécuter `git push`** — seul l'utilisateur pousse.

## Formes de données de l'API Scalingo

Relevées dans le client officiel `Scalingo/go-scalingo` (`scm_repo_link.go`, `deployments.go`, `apps.go`) — ce sont les noms de champs à utiliser, pas des suppositions.

```
GET /v1/apps/{parent}/scm_repo_link/review_apps
→ {"review_apps": [ReviewApp]}

ReviewApp = {
  "id": str, "app_id": str, "app_name": str,
  "parent_app_id": str, "parent_app_name": str,
  "pull_request": {"number": int, "branch_name": str, "title": str, "html_url": str, "ref": str, "base_ref": str},
  "last_deployment": Deployment | null
}

Deployment = {"id": str, "status": str, "git_ref": str, ...}
  status ∈ success | queued | building | starting | pushing | aborted
         | build-error | crashed-error | timeout-error | hook-error

POST /v1/apps/{parent}/scm_repo_link/manual_review_app   body {"pull_request_id": int}
DELETE /v1/apps/{app_name}                               body {"current_name": app_name}
```

URL publique d'une review app : `https://{app_name}.osc-fr1.scalingo.io` — motif documenté dans le commentaire de `scalingo.json`, confirmé en Task 8.

## Structure des fichiers

| Fichier | Responsabilité |
|---|---|
| `scripts/review_app.py` (créer) | Toute la logique : échange de token, lecture d'état, décision de réconciliation, destruction, CLI |
| `tests/test_review_app.py` (créer) | Couverture des trois états de réconciliation, de l'idempotence de la destruction, et du contrat de la CLI |
| `.github/workflows/ci.yml` (modifier) | Ajout des `types` du déclencheur et du job `review-app` |
| `.github/workflows/review-app-teardown.yml` (créer) | Destruction et passage du déploiement GitHub à `inactive` |
| `README.md` (modifier) | Section review apps : ce qu'elles contiennent, pourquoi elles sont internes |

Un seul module Python : la logique tient en une centaine de lignes et tout y change ensemble. Le découper serait de l'abstraction prématurée.

---

### Task 1: Échange de token et lecture de l'état

**Files:**
- Create: `scripts/review_app.py`
- Create: `tests/test_review_app.py`

**Interfaces:**
- Consumes: rien.
- Produces:
  - `exchange_token(client: httpx.Client, api_token: str) -> str`
  - `find_review_app(client: httpx.Client, bearer: str, parent_app: str, pr_number: int) -> dict | None`
  - `app_url(app_name: str) -> str`
  - Constantes `AUTH_URL`, `API_URL`, `TIMEOUT`

- [ ] **Step 1: Write the failing test**

Créer `tests/test_review_app.py` :

```python
import importlib.util
import io
import json
from pathlib import Path

import httpx
import pytest

spec = importlib.util.spec_from_file_location(
    "review_app", Path(__file__).parent.parent / "scripts" / "review_app.py"
)
review_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review_app)


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload if payload is not None else {}
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPError(f"HTTP {self.status_code}")


class FakeClient:
    """Client httpx factice : rejoue des réponses programmées et enregistre les appels."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs.get("json")))
        return self.responses.pop(0)

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs.get("json")))
        return self.responses.pop(0)

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs.get("json")))
        return self.responses.pop(0)


def listing(*review_apps):
    return {"review_apps": list(review_apps)}


def review_app_entry(pr_number=42, git_ref="abc123", app_name="autometa-staging-pr42"):
    return {
        "id": "ra-1",
        "app_id": "app-1",
        "app_name": app_name,
        "pull_request": {"number": pr_number},
        "last_deployment": {"id": "d-1", "status": "success", "git_ref": git_ref},
    }


def test_exchange_token_returns_bearer():
    client = FakeClient([FakeResponse({"token": "jwt-value"})])

    assert review_app.exchange_token(client, "tk-us-secret") == "jwt-value"
    assert client.calls[0][1] == review_app.AUTH_URL


def test_find_review_app_matches_on_pull_request_number():
    payload = listing(review_app_entry(pr_number=7, app_name="autometa-staging-pr7"), review_app_entry(pr_number=42))
    client = FakeClient([FakeResponse(payload)])

    found = review_app.find_review_app(client, "jwt", "autometa-staging", 42)

    assert found["app_name"] == "autometa-staging-pr42"


def test_find_review_app_returns_none_when_absent():
    client = FakeClient([FakeResponse(listing())])

    assert review_app.find_review_app(client, "jwt", "autometa-staging", 42) is None


def test_app_url_uses_scalingo_domain():
    assert review_app.app_url("autometa-staging-pr42") == "https://autometa-staging-pr42.osc-fr1.scalingo.io"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_review_app.py -v`
Expected: FAIL — `FileNotFoundError` sur `scripts/review_app.py`.

- [ ] **Step 3: Write minimal implementation**

Créer `scripts/review_app.py` :

```python
"""Réconcilie les review apps Scalingo avec le cycle de vie des pull requests GitHub."""

AUTH_URL = "https://auth.scalingo.com/v1/tokens/exchange"
API_URL = "https://api.osc-fr1.scalingo.com/v1"
TIMEOUT = 30.0


def exchange_token(client, api_token):
    """Échange un token API Scalingo contre un bearer JWT de courte durée."""
    response = client.post(AUTH_URL, auth=("", api_token), timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()["token"]


def find_review_app(client, bearer, parent_app, pr_number):
    """La review app rattachée à cette PR, ou None."""
    response = client.get(
        f"{API_URL}/apps/{parent_app}/scm_repo_link/review_apps",
        headers={"Authorization": f"Bearer {bearer}"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    for entry in response.json()["review_apps"]:
        if entry["pull_request"]["number"] == pr_number:
            return entry
    return None


def app_url(app_name):
    return f"https://{app_name}.osc-fr1.scalingo.io"
```

Le module n'importe pas `httpx` à ce stade : le client est injecté en paramètre, ce qui rend les fonctions testables sans mock et évite un F401. L'import arrive en Task 4, où `main` instancie le client.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_review_app.py -v`
Expected: PASS — 4 tests.

- [ ] **Step 5: Lint**

Run: `uv run ruff check scripts/review_app.py tests/test_review_app.py && uv run ruff format --check scripts/review_app.py tests/test_review_app.py`
Expected: pas d'erreur. Si `ruff format` échoue, lancer `uv run ruff format scripts/review_app.py tests/test_review_app.py`.

- [ ] **Step 6: Commit**

```bash
git add scripts/review_app.py tests/test_review_app.py
git commit -m "feat(ci): read Scalingo review app state for a pull request"
```

---

### Task 2: Réconciliation `ensure`

**Files:**
- Modify: `scripts/review_app.py`
- Modify: `tests/test_review_app.py`

**Interfaces:**
- Consumes: `find_review_app`, `app_url`, `API_URL`, `TIMEOUT` (Task 1).
- Produces:
  - `deploy_review_app(client, bearer, parent_app: str, pr_number: int) -> None`
  - `deployed_ref(entry: dict) -> str | None`
  - `ensure(client, bearer, parent_app: str, pr_number: int, sha: str) -> dict` renvoyant `{"action": "created"|"updated"|"noop", "app": str, "url": str}`

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_review_app.py` :

```python
@pytest.mark.parametrize(
    ("payload", "expected_action", "expected_posts"),
    [
        (listing(), "created", 1),
        (listing(review_app_entry(git_ref="abc123")), "noop", 0),
        (listing(review_app_entry(git_ref="staleref")), "updated", 1),
    ],
)
def test_ensure_reconciles_against_head_sha(payload, expected_action, expected_posts):
    client = FakeClient([FakeResponse(payload)] + [FakeResponse()] * expected_posts)

    result = review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")

    assert result["action"] == expected_action
    assert result["app"] == "autometa-staging-pr42"
    assert result["url"] == "https://autometa-staging-pr42.osc-fr1.scalingo.io"
    posts = [call for call in client.calls if call[0] == "POST"]
    assert len(posts) == expected_posts


def test_ensure_posts_the_pull_request_id():
    client = FakeClient([FakeResponse(listing()), FakeResponse()])

    review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")

    method, url, body = client.calls[1]
    assert method == "POST"
    assert url.endswith("/apps/autometa-staging/scm_repo_link/manual_review_app")
    assert body == {"pull_request_id": 42}


def test_ensure_redeploys_when_deployment_is_missing():
    entry = review_app_entry()
    entry["last_deployment"] = None
    client = FakeClient([FakeResponse(listing(entry)), FakeResponse()])

    result = review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")

    assert result["action"] == "updated"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_review_app.py -k ensure -v`
Expected: FAIL — `AttributeError: module 'review_app' has no attribute 'ensure'`.

- [ ] **Step 3: Write minimal implementation**

Ajouter à `scripts/review_app.py` :

```python
def deploy_review_app(client, bearer, parent_app, pr_number):
    response = client.post(
        f"{API_URL}/apps/{parent_app}/scm_repo_link/manual_review_app",
        headers={"Authorization": f"Bearer {bearer}"},
        json={"pull_request_id": pr_number},
        timeout=TIMEOUT,
    )
    response.raise_for_status()


def deployed_ref(entry):
    deployment = entry.get("last_deployment")
    return deployment["git_ref"] if deployment else None


def ensure(client, bearer, parent_app, pr_number, sha):
    """Amène la review app de la PR à l'état voulu, quel que soit l'état constaté."""
    entry = find_review_app(client, bearer, parent_app, pr_number)
    name = entry["app_name"] if entry else f"{parent_app}-pr{pr_number}"
    if entry and deployed_ref(entry) == sha:
        return {"action": "noop", "app": name, "url": app_url(name)}
    deploy_review_app(client, bearer, parent_app, pr_number)
    return {"action": "updated" if entry else "created", "app": name, "url": app_url(name)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_review_app.py -v`
Expected: PASS — 9 tests.

- [ ] **Step 5: Lint**

Run: `uv run ruff check scripts/ tests/test_review_app.py && uv run ruff format --check scripts/ tests/test_review_app.py`

- [ ] **Step 6: Commit**

```bash
git add scripts/review_app.py tests/test_review_app.py
git commit -m "feat(ci): reconcile review app deployment with pull request head"
```

---

### Task 3: Destruction idempotente

**Files:**
- Modify: `scripts/review_app.py`
- Modify: `tests/test_review_app.py`

**Interfaces:**
- Consumes: `find_review_app`, `API_URL`, `TIMEOUT` (Task 1).
- Produces: `destroy(client, bearer, parent_app: str, pr_number: int) -> dict` renvoyant `{"action": "destroyed"|"absent", "app": str | None}`

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_review_app.py` :

```python
def test_destroy_removes_the_review_app():
    client = FakeClient([FakeResponse(listing(review_app_entry())), FakeResponse()])

    result = review_app.destroy(client, "jwt", "autometa-staging", 42)

    assert result == {"action": "destroyed", "app": "autometa-staging-pr42"}
    method, url, body = client.calls[1]
    assert method == "DELETE"
    assert url.endswith("/apps/autometa-staging-pr42")
    assert body == {"current_name": "autometa-staging-pr42"}


def test_destroy_is_a_noop_when_already_gone():
    client = FakeClient([FakeResponse(listing())])

    result = review_app.destroy(client, "jwt", "autometa-staging", 42)

    assert result == {"action": "absent", "app": None}
    assert all(call[0] != "DELETE" for call in client.calls)


def test_destroy_tolerates_a_404_from_scalingo():
    client = FakeClient([FakeResponse(listing(review_app_entry())), FakeResponse(status_code=404)])

    result = review_app.destroy(client, "jwt", "autometa-staging", 42)

    assert result == {"action": "absent", "app": "autometa-staging-pr42"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_review_app.py -k destroy -v`
Expected: FAIL — `AttributeError: module 'review_app' has no attribute 'destroy'`.

- [ ] **Step 3: Write minimal implementation**

Ajouter à `scripts/review_app.py` :

```python
def destroy(client, bearer, parent_app, pr_number):
    """Supprime la review app de la PR. Une review app déjà absente vaut succès."""
    entry = find_review_app(client, bearer, parent_app, pr_number)
    if entry is None:
        return {"action": "absent", "app": None}
    name = entry["app_name"]
    response = client.request(
        "DELETE",
        f"{API_URL}/apps/{name}",
        headers={"Authorization": f"Bearer {bearer}"},
        json={"current_name": name},
        timeout=TIMEOUT,
    )
    if response.status_code == 404:
        return {"action": "absent", "app": name}
    response.raise_for_status()
    return {"action": "destroyed", "app": name}
```

L'idempotence est intentionnelle et pas défensive : `delete_on_close_enabled` est actif côté Scalingo, qui aura donc le plus souvent déjà détruit la review app quand ce code s'exécute.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_review_app.py -v`
Expected: PASS — 12 tests.

- [ ] **Step 5: Lint**

Run: `uv run ruff check scripts/ tests/test_review_app.py && uv run ruff format --check scripts/ tests/test_review_app.py`

- [ ] **Step 6: Commit**

```bash
git add scripts/review_app.py tests/test_review_app.py
git commit -m "feat(ci): destroy a review app idempotently when its PR closes"
```

---

### Task 4: Interface en ligne de commande

**Files:**
- Modify: `scripts/review_app.py`
- Modify: `tests/test_review_app.py`

**Interfaces:**
- Consumes: `exchange_token`, `ensure`, `destroy`.
- Produces: `main(argv: list[str] | None = None) -> int`. Contrat : le token API est lu sur **stdin**, le résultat est écrit sur **stdout** en JSON sur une ligne. Codes de sortie : `0` succès, `2` erreur d'arguments (argparse).

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_review_app.py` :

```python
class NullClient:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_main_ensure_prints_json_and_never_leaks_the_bearer(mocker, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("tk-us-secret\n"))
    mocker.patch.object(review_app.httpx, "Client", return_value=NullClient())
    mocker.patch.object(review_app, "exchange_token", return_value="jwt-bearer")
    mocker.patch.object(
        review_app,
        "ensure",
        return_value={"action": "created", "app": "autometa-staging-pr42", "url": "https://x"},
    )

    exit_code = review_app.main(["ensure", "--app", "autometa-staging", "--pr", "42", "--sha", "abc123"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert json.loads(out) == {"action": "created", "app": "autometa-staging-pr42", "url": "https://x"}
    assert "jwt-bearer" not in out
    assert "tk-us-secret" not in out


def test_main_destroy_does_not_require_a_sha(mocker, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("tk-us-secret\n"))
    mocker.patch.object(review_app.httpx, "Client", return_value=NullClient())
    mocker.patch.object(review_app, "exchange_token", return_value="jwt-bearer")
    destroy = mocker.patch.object(review_app, "destroy", return_value={"action": "absent", "app": None})

    assert review_app.main(["destroy", "--app", "autometa-staging", "--pr", "42"]) == 0
    destroy.assert_called_once()
    assert json.loads(capsys.readouterr().out)["action"] == "absent"


def test_main_rejects_ensure_without_sha(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("tk-us-secret\n"))

    with pytest.raises(SystemExit) as excinfo:
        review_app.main(["ensure", "--app", "autometa-staging", "--pr", "42"])

    assert excinfo.value.code == 2
```

`io` et `json` ont été ajoutés aux imports du fichier de test en Task 1 : rien à changer en tête.

Le spec évoquait un `::add-mask::` sur le bearer. Il est inutile ici et remplacé par une garantie plus forte : le bearer ne sort jamais du processus, et `test_main_ensure_prints_json_and_never_leaks_the_bearer` le vérifie. Les secrets de workflow, eux, sont masqués nativement par GitHub.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_review_app.py -k main -v`
Expected: FAIL — `AttributeError: module 'review_app' has no attribute 'main'`.

- [ ] **Step 3: Write minimal implementation**

En tête de `scripts/review_app.py`, compléter les imports :

```python
import argparse
import json
import sys

import httpx
```

Puis ajouter en fin de module :

```python
def main(argv=None):
    parser = argparse.ArgumentParser(description="Réconcilie une review app Scalingo avec sa pull request.")
    parser.add_argument("command", choices=["ensure", "destroy"])
    parser.add_argument("--app", required=True, help="Application parente Scalingo")
    parser.add_argument("--pr", type=int, required=True, help="Numéro de la pull request")
    parser.add_argument("--sha", help="head.sha de la PR, requis pour ensure")
    args = parser.parse_args(argv)
    if args.command == "ensure" and not args.sha:
        parser.error("--sha est requis pour ensure")

    api_token = sys.stdin.read().strip()
    with httpx.Client() as client:
        bearer = exchange_token(client, api_token)
        if args.command == "ensure":
            result = ensure(client, bearer, args.app, args.pr, args.sha)
        else:
            result = destroy(client, bearer, args.app, args.pr)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest tests/test_review_app.py -v`
Expected: PASS — 15 tests.

- [ ] **Step 5: Vérifier la couverture du diff**

Run: `uv run pytest tests/test_review_app.py --cov=scripts.review_app --cov-report=term-missing`
Expected: aucune ligne manquante hors du bloc `if __name__ == "__main__":`. Le seuil `diff-cover` du dépôt est de 90 % ; si des lignes manquent, ajouter le test correspondant plutôt que d'abaisser le seuil.

- [ ] **Step 6: Lint et commit**

```bash
uv run ruff check scripts/ tests/test_review_app.py
uv run ruff format --check scripts/ tests/test_review_app.py
git add scripts/review_app.py tests/test_review_app.py
git commit -m "feat(ci): expose review app reconciliation as a CLI reading its token from stdin"
```

---

### Task 5: Job `review-app` dans la CI

**Files:**
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `scripts/review_app.py ensure` (Task 4).
- Produces: un déploiement GitHub `review-app-pr-<N>` en état `success`, portant l'URL de la review app.

- [ ] **Step 1: Étendre le déclencheur `pull_request`**

Dans `.github/workflows/ci.yml`, remplacer :

```yaml
on:
  pull_request:
```

par :

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
```

`ready_for_review` est indispensable : sans lui, une PR passée de draft à prête n'obtiendrait jamais sa review app.

- [ ] **Step 2: Ajouter le job**

À la fin de `.github/workflows/ci.yml`, après le job `docker` :

```yaml
  review-app:
    name: Review app
    needs: [lint, security, test, migrations]
    if: >-
      github.event_name == 'pull_request'
      && github.event.pull_request.head.repo.full_name == github.repository
      && !github.event.pull_request.draft
    runs-on: ubuntu-latest
    environment: review-app
    permissions:
      contents: read
      deployments: write
    concurrency:
      group: review-app-pr-${{ github.event.pull_request.number }}
      cancel-in-progress: false
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2
        with:
          ref: ${{ github.event.pull_request.base.sha }}
          persist-credentials: false

      - uses: astral-sh/setup-uv@37802adc94f370d6bfd71619e3f0bf239e1f3b78 # v7.6.0
        with:
          enable-cache: true

      - run: uv sync --group dev --frozen

      - name: Reconcile review app
        id: reconcile
        env:
          SCALINGO_TOKEN: ${{ secrets.SCALINGO_REVIEW_APP_TOKEN }}
          PR: ${{ github.event.pull_request.number }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
        run: |
          result=$(printf '%s' "$SCALINGO_TOKEN" \
            | uv run python scripts/review_app.py ensure --app autometa-staging --pr "$PR" --sha "$HEAD_SHA")
          echo "$result"
          echo "url=$(echo "$result" | jq -r .url)" >> "$GITHUB_OUTPUT"

      - name: Publish GitHub deployment
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
          PR: ${{ github.event.pull_request.number }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
          URL: ${{ steps.reconcile.outputs.url }}
        run: |
          deployment_id=$(jq -n --arg ref "$HEAD_SHA" --arg env "review-app-pr-$PR" \
            '{ref: $ref, environment: $env, auto_merge: false, required_contexts: [],
              transient_environment: true, description: "Scalingo review app"}' \
            | gh api "repos/$REPO/deployments" --input - --jq .id)
          jq -n --arg url "$URL" '{state: "success", environment_url: $url, description: "Review app déployée"}' \
            | gh api "repos/$REPO/deployments/$deployment_id/statuses" --input - > /dev/null
```

Le JSON est construit par `jq -n` et non par un heredoc. Un heredoc dans un scalaire de bloc YAML est un piège : le délimiteur de fin doit respecter l'indentation du bloc, faute de quoi le YAML est invalide ou le script silencieusement tronqué. `jq -n --arg` échappe en prime les valeurs, ce qu'une interpolation de chaîne ne fait pas.

Trois points qui ne s'improvisent pas :

- `ref: ${{ github.event.pull_request.base.sha }}` — le checkout porte sur la base, jamais sur le head. Le job n'a besoin que du numéro de PR ; sans cette ligne, une PR pourrait réécrire `scripts/review_app.py` pour exfiltrer le token.
- `persist-credentials: false` — évite de laisser le `GITHUB_TOKEN` dans la configuration git du runner.
- `needs` exclut `docker` : Scalingo déploie par buildpacks, l'image ne conditionne rien.

- [ ] **Step 3: Valider la syntaxe du workflow**

Run: `uv run python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"`
Expected: `yaml ok`

- [ ] **Step 4: Vérifier que rien d'autre n'a bougé**

Run: `git diff --stat .github/workflows/ci.yml`
Expected: uniquement des ajouts, plus la ligne `types:`. Aucun job existant modifié.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "feat(ci): create or update the review app once the PR checks pass"
```

---

### Task 6: Workflow de teardown

**Files:**
- Create: `.github/workflows/review-app-teardown.yml`

**Interfaces:**
- Consumes: `scripts/review_app.py destroy` (Task 4).
- Produces: review app détruite et déploiements GitHub de `review-app-pr-<N>` passés à `inactive`.

- [ ] **Step 1: Créer le workflow**

```yaml
name: Review app teardown

on:
  pull_request:
    types: [closed]

permissions:
  contents: read

jobs:
  teardown:
    name: Destroy review app
    if: github.event.pull_request.head.repo.full_name == github.repository
    runs-on: ubuntu-latest
    environment: review-app
    permissions:
      contents: read
      deployments: write
    concurrency:
      group: review-app-pr-${{ github.event.pull_request.number }}
      cancel-in-progress: false
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2
        with:
          ref: ${{ github.event.pull_request.base.ref }}
          persist-credentials: false

      - uses: astral-sh/setup-uv@37802adc94f370d6bfd71619e3f0bf239e1f3b78 # v7.6.0
        with:
          enable-cache: true

      - run: uv sync --group dev --frozen

      - name: Destroy review app
        env:
          SCALINGO_TOKEN: ${{ secrets.SCALINGO_REVIEW_APP_TOKEN }}
          PR: ${{ github.event.pull_request.number }}
        run: |
          printf '%s' "$SCALINGO_TOKEN" \
            | uv run python scripts/review_app.py destroy --app autometa-staging --pr "$PR"

      - name: Mark GitHub deployments inactive
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
          PR: ${{ github.event.pull_request.number }}
        run: |
          for id in $(gh api "repos/$REPO/deployments?environment=review-app-pr-$PR" --jq '.[].id'); do
            jq -n '{state: "inactive", description: "Review app détruite"}' \
              | gh api "repos/$REPO/deployments/$id/statuses" --input - > /dev/null
          done
```

Le checkout porte sur `base.ref` — la branche de destination, donc `main` — et non sur le head de la PR : à ce stade la branche source peut déjà avoir été supprimée, et on ne veut de toute façon exécuter que du code relu.

- [ ] **Step 2: Valider la syntaxe**

Run: `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/review-app-teardown.yml')); print('yaml ok')"`
Expected: `yaml ok`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/review-app-teardown.yml
git commit -m "feat(ci): tear down the review app when its pull request closes"
```

---

### Task 7: Documentation

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: rien.
- Produces: rien de consommé par une autre tâche.

- [ ] **Step 1: Ajouter la section**

Dans `README.md`, après la section `### Scalingo` (qui se termine par la liste des fichiers de configuration, ligne ~178), insérer :

```markdown
### Review apps

Chaque pull request interne non-draft obtient une review app Scalingo, créée par la CI une fois
lint, tests et migrations au vert, puis détruite à la fermeture de la PR. L'URL apparaît dans
l'encart de déploiement de la PR.

Une review app est un enfant de `autometa-staging` : elle **hérite de ses variables
d'environnement**, donc de vraies clés Matomo, Metabase, S3 et du token Anthropic. Sa base de
données, elle, est vide — Scalingo ne copie jamais le contenu des addons.

C'est la raison pour laquelle les pull requests venant de forks n'en obtiennent pas, et n'en
obtiendront pas : cf. le bulletin Scalingo SSB-2023-001. Pour prévisualiser une contribution
externe, pousser la branche dans le dépôt et ouvrir une PR interne.

Conception et décisions : `docs/plans/2026-08-11-review-apps-ci-design.md`.
```

- [ ] **Step 2: Vérifier le rendu**

Run: `git diff README.md`
Expected: un seul bloc ajouté, aucune ligne existante modifiée.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: describe CI-driven review apps and why forks are excluded"
```

---

### Task 8: Validation de bout en bout

**Files:** aucun fichier de code. Cette tâche produit des faits, et le cas échéant un correctif.

**Interfaces:**
- Consumes: tout ce qui précède.
- Produces: confirmation ou infirmation des deux hypothèses restantes du spec.

**Contrainte d'amorçage, à lire avant de commencer :** le job de la Task 5 fait son checkout sur `base.sha`. Sur la PR qui *introduit* `scripts/review_app.py`, ce fichier n'existe pas encore dans la base — le job échouera donc sur cette PR-là, et c'est normal. La validation se fait sur une PR jetable ouverte **après** la fusion de ce travail dans `main`.

- [ ] **Step 1: Faire relire et fusionner le travail**

Ce changement touche l'infrastructure de déploiement et les permissions de la CI : relecture humaine obligatoire. Ne pas pousser soi-même — c'est l'utilisateur qui pousse.

- [ ] **Step 2: Ouvrir une PR jetable**

Depuis `main` à jour, une branche avec une modification triviale (une ligne dans un fichier de documentation), puis une PR interne non-draft.

- [ ] **Step 3: Vérifier la création**

Attendre le vert de la CI, puis :

```bash
scalingo --app autometa-staging review-apps
```

Expected: une review app pour cette PR. Vérifier que l'encart de déploiement apparaît dans la PR et que son URL répond.

- [ ] **Step 4: Vérifier l'hypothèse « POST sur une review app existante »**

Pousser un second commit sur la branche, attendre la fin de la CI, puis relancer le workflow **une troisième fois** sans nouveau commit (« Re-run all jobs »).

Expected au second commit : `{"action": "updated"}` ou `{"action": "noop"}` selon que le webhook Scalingo a déjà redéployé — les deux sont corrects, la logique est convergente.
Expected au re-run sans commit : `{"action": "noop"}`, sans appel POST.

Si le second commit produit une erreur HTTP 409 ou 422 sur `manual_review_app`, l'hypothèse du spec est infirmée. Correctif : dans `ensure`, remplacer l'appel à `deploy_review_app` par un `POST {API_URL}/apps/{entry["app_name"]}/scm_repo_link/manual_deploy` avec `{"branch": entry["pull_request"]["branch_name"]}` **uniquement dans la branche « updated »**, la branche « created » restant sur `manual_review_app`. Ajouter le test correspondant avant le correctif.

- [ ] **Step 5: Vérifier les deux conventions de nommage**

Expected: le nom de l'app est `autometa-staging-pr<N>` et son URL `https://autometa-staging-pr<N>.osc-fr1.scalingo.io`. Si le motif diffère, corriger `ensure` pour utiliser le nom renvoyé par l'API après création plutôt que la convention, et ajouter le test.

- [ ] **Step 6: Vérifier la destruction**

Fermer la PR sans fusionner, puis :

```bash
scalingo --app autometa-staging review-apps
```

Expected: plus de review app pour cette PR, workflow de teardown au vert, et déploiement GitHub passé à `inactive` dans l'onglet Environments du dépôt.

- [ ] **Step 7: Vérifier le refus des forks**

Sur la même PR jetable, contrôler dans l'onglet Actions que le job `review-app` est bien marqué *skipped* si la PR provient d'un fork. À défaut de fork sous la main, relire la condition `if:` — c'est le seul contrôle qui protège les identifiants.

- [ ] **Step 8: Faire tourner la CI en local**

Run: `make ci`
Expected: lint, security et tests au vert.

- [ ] **Step 9: Renouveler le token**

Le token initial a transité en clair hors d'un canal sécurisé. Depuis le dashboard Scalingo connecté en `reviewapp.autometa`, générer un nouveau token, révoquer l'ancien, puis :

```bash
gh secret set SCALINGO_REVIEW_APP_TOKEN --env review-app --repo gip-inclusion/autometa
```

Relancer le workflow d'une PR ouverte pour confirmer que la chaîne fonctionne avec le nouveau token.

- [ ] **Step 10: Consigner les résultats**

Mettre à jour la section « Vérifications effectuées » de `docs/plans/2026-08-11-review-apps-ci-design.md` avec ce qui a été observé, en particulier le comportement de `manual_review_app` sur une review app existante, et supprimer la mention « à vérifier en premier à l'implémentation » de la section Réconciliation.

```bash
git add docs/plans/2026-08-11-review-apps-ci-design.md
git commit -m "docs: record end-to-end validation results for review apps"
```

---

## Relecture humaine

Ce changement touche l'infrastructure de déploiement et les permissions de la CI. Il nécessite une relecture humaine avant fusion.
