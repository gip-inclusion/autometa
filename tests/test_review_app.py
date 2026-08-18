import importlib.util
import io
import json
from pathlib import Path

import httpx
import pytest

spec = importlib.util.spec_from_file_location("review_app", Path(__file__).parent.parent / "scripts" / "review_app.py")
review_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review_app)


class FakeResponse:
    """Réponse factice. `payload=None` modélise un corps vide, sur lequel `.json()` échoue."""

    def __init__(self, payload=None, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        if self.payload is None:
            raise json.JSONDecodeError("Expecting value", "", 0)
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPError(f"HTTP {self.status_code}")


class FakeClient:
    """Client httpx factice : rejoue des réponses programmées et enregistre les appels."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def record(self, method, url, kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)

    def get(self, url, **kwargs):
        return self.record("GET", url, kwargs)

    def post(self, url, **kwargs):
        return self.record("POST", url, kwargs)

    def request(self, method, url, **kwargs):
        return self.record(method, url, kwargs)


def listing(*review_apps):
    return {"review_apps": list(review_apps)}


def review_app_entry(pr_number=42, git_ref="abc123", app_name="autometa-staging-pr42", branch="feature"):
    return {
        "id": "ra-1",
        "app_id": "app-1",
        "app_name": app_name,
        "pull_request": {"number": pr_number, "branch_name": branch},
        "last_deployment": {"id": "d-1", "status": "success", "git_ref": git_ref},
    }


def created(app_name="autometa-staging-pr42", branch="feature"):
    """Corps du POST manual_review_app : la review app est imbriquée sous `review_app`."""
    return {"review_app": review_app_entry(app_name=app_name, branch=branch)}


def link(delete_on_close=True):
    return {"scm_repo_link": {"delete_on_close_enabled": delete_on_close, "hours_before_delete_on_close": 0}}


def addons(*statuses):
    return {"addons": [{"id": f"ad-{i}", "status": s} for i, s in enumerate(statuses)]}


def deployment(status="queued"):
    return {"deployment": {"id": "dep-1", "status": status, "git_ref": "abc123"}}


def creation_flow(*, entry_listing, app_name="autometa-staging-pr42"):
    """Les réponses que `ensure` consomme sur le chemin de création."""
    return [
        FakeResponse(link()),
        FakeResponse(entry_listing),
        FakeResponse(created(app_name)),
        FakeResponse(addons("running", "running")),
        FakeResponse(deployment()),
        FakeResponse(deployment("success")),
    ]


def test_exchange_token_returns_bearer():
    client = FakeClient([FakeResponse({"token": "jwt-value"})])

    assert review_app.exchange_token(client, "tk-us-secret") == "jwt-value"
    method, url, kwargs = client.calls[0]
    assert (method, url) == ("POST", review_app.AUTH_URL)
    assert kwargs["auth"] == ("", "tk-us-secret")
    assert kwargs["timeout"] == review_app.TIMEOUT


def read_state(client):
    return review_app.find_review_app(client, "jwt", "autometa-staging", 42)


def read_link(client):
    return review_app.scm_repo_link(client, "jwt", "autometa-staging")


def create_app(client):
    return review_app.create_review_app(client, "jwt", "autometa-staging", 42)


def deploy_app(client):
    return review_app.deploy(client, "jwt", "autometa-staging-pr42", "feature")


def follow_deployment(client):
    return review_app.wait_for_deployment(client, "jwt", "autometa-staging-pr42", "dep-1")


def stop_app(client):
    return review_app.stop(client, "jwt", "autometa-staging", 42)


@pytest.mark.parametrize(
    ("operation", "responses"),
    [
        (read_state, [FakeResponse(listing())]),
        (read_link, [FakeResponse(link())]),
        (create_app, [FakeResponse(created())]),
        (deploy_app, [FakeResponse(deployment())]),
        (follow_deployment, [FakeResponse(deployment("success"))]),
        (stop_app, [FakeResponse(listing(review_app_entry())), FakeResponse({})]),
    ],
    ids=["read_state", "read_link", "create", "deploy", "follow", "stop"],
)
def test_scalingo_calls_carry_the_bearer_and_a_timeout(operation, responses):
    client = FakeClient(responses)

    operation(client)

    assert len(client.calls) == len(responses)
    for _, _, kwargs in client.calls:
        assert kwargs["headers"] == {"Authorization": "Bearer jwt"}
        assert kwargs["timeout"]


def test_create_review_app_gets_a_longer_timeout_than_the_read_calls():
    """La création provisionne les addons : mesurée à 17 s, elle dépasse le timeout courant."""
    client = FakeClient([FakeResponse(created())])

    review_app.create_review_app(client, "jwt", "autometa-staging", 42)

    assert client.calls[0][2]["timeout"] > review_app.TIMEOUT


def test_find_review_app_matches_on_pull_request_number():
    payload = listing(review_app_entry(pr_number=7, app_name="autometa-staging-pr7"), review_app_entry(pr_number=42))
    client = FakeClient([FakeResponse(payload)])

    found = review_app.find_review_app(client, "jwt", "autometa-staging", 42)

    assert found["app_name"] == "autometa-staging-pr42"


def test_find_review_app_ignores_entries_without_a_pull_request():
    orphan = review_app_entry(app_name="autometa-staging-orphan")
    orphan["pull_request"] = None
    client = FakeClient([FakeResponse(listing(orphan, review_app_entry()))])

    found = review_app.find_review_app(client, "jwt", "autometa-staging", 42)

    assert found["app_name"] == "autometa-staging-pr42"


def test_find_review_app_returns_none_when_absent():
    client = FakeClient([FakeResponse(listing())])

    assert review_app.find_review_app(client, "jwt", "autometa-staging", 42) is None


def test_app_url_uses_scalingo_domain():
    assert review_app.app_url("autometa-staging-pr42") == "https://autometa-staging-pr42.osc-fr1.scalingo.io"


def test_ensure_refuses_to_run_when_scalingo_would_never_delete_the_app():
    """`delete_on_close_enabled` est la seule chose qui détruit les review apps : la CI n'en a pas le droit."""
    client = FakeClient([FakeResponse(link(delete_on_close=False))])

    with pytest.raises(RuntimeError, match="delete_on_close_enabled"):
        review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")

    assert len(client.calls) == 1


def test_ensure_creates_then_waits_for_addons_then_deploys():
    """`manual_review_app` crée l'app sans la déployer, et DATABASE_URL n'existe qu'une fois les addons prêts."""
    client = FakeClient(creation_flow(entry_listing=listing()))

    result = review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")

    assert result == {
        "action": "created",
        "app": "autometa-staging-pr42",
        "url": "https://autometa-staging-pr42.osc-fr1.scalingo.io",
    }
    assert [(method, url.rsplit("/v1", 1)[-1]) for method, url, _ in client.calls] == [
        ("GET", "/apps/autometa-staging/scm_repo_link"),
        ("GET", "/apps/autometa-staging/scm_repo_link/review_apps"),
        ("POST", "/apps/autometa-staging/scm_repo_link/manual_review_app"),
        ("GET", "/apps/autometa-staging-pr42/addons"),
        ("POST", "/apps/autometa-staging-pr42/scm_repo_link/manual_deploy"),
        ("GET", "/apps/autometa-staging-pr42/deployments/dep-1"),
    ]


def test_ensure_posts_the_pull_request_id_when_creating():
    client = FakeClient(creation_flow(entry_listing=listing()))

    review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")

    assert client.calls[2][2]["json"] == {"pull_request_id": 42}


def test_ensure_deploys_the_pull_request_branch():
    client = FakeClient(creation_flow(entry_listing=listing()))

    review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")

    assert client.calls[4][2]["json"] == {"branch": "feature"}


def test_ensure_redeploys_an_existing_app_without_creating_it_again():
    """Un second `manual_review_app` renvoie 500 « name has already been taken » : il ne faut pas l'appeler."""
    client = FakeClient([
        FakeResponse(link()),
        FakeResponse(listing(review_app_entry(git_ref="staleref"))),
        FakeResponse(deployment()),
        FakeResponse(deployment("success")),
    ])

    result = review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")

    assert result["action"] == "updated"
    assert [(method, url.rsplit("/v1", 1)[-1]) for method, url, _ in client.calls] == [
        ("GET", "/apps/autometa-staging/scm_repo_link"),
        ("GET", "/apps/autometa-staging/scm_repo_link/review_apps"),
        ("POST", "/apps/autometa-staging-pr42/scm_repo_link/manual_deploy"),
        ("GET", "/apps/autometa-staging-pr42/deployments/dep-1"),
    ]


def test_ensure_does_nothing_when_the_head_sha_is_already_deployed():
    client = FakeClient([FakeResponse(link()), FakeResponse(listing(review_app_entry(git_ref="abc123")))])

    result = review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")

    assert result["action"] == "noop"
    assert all(method != "POST" for method, _, _ in client.calls)


@pytest.mark.parametrize(
    "deployment_state",
    [
        None,
        {"id": "d-1", "status": "build-error", "git_ref": "abc123"},
        {"id": "d-1", "status": "hook-error", "git_ref": "abc123"},
    ],
    ids=["never deployed", "build-error", "hook-error"],
)
def test_ensure_redeploys_unless_the_sha_is_successfully_deployed(deployment_state):
    entry = review_app_entry()
    entry["last_deployment"] = deployment_state
    client = FakeClient([
        FakeResponse(link()),
        FakeResponse(listing(entry)),
        FakeResponse(deployment()),
        FakeResponse(deployment("success")),
    ])

    assert review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")["action"] == "updated"


def test_ensure_uses_the_app_name_returned_by_scalingo():
    client = FakeClient(creation_flow(entry_listing=listing(), app_name="autometa-staging-pr42-b7c1"))

    result = review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")

    assert result["app"] == "autometa-staging-pr42-b7c1"
    assert result["url"] == "https://autometa-staging-pr42-b7c1.osc-fr1.scalingo.io"


def test_ensure_propagates_a_failed_creation():
    """Le fake doit pouvoir échouer : c'est ce qui manquait quand le 500 de Scalingo est passé inaperçu."""
    client = FakeClient([FakeResponse(link()), FakeResponse(listing()), FakeResponse(status_code=500)])

    with pytest.raises(httpx.HTTPError):
        review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")


def test_ensure_propagates_a_refused_deployment():
    client = FakeClient([
        FakeResponse(link()),
        FakeResponse(listing(review_app_entry(git_ref="stale"))),
        FakeResponse(status_code=401),
    ])

    with pytest.raises(httpx.HTTPError):
        review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")


@pytest.mark.parametrize("status", ["hook-error", "build-error", "crashed-error", "aborted"])
def test_ensure_fails_when_the_build_does_not_succeed(status):
    """Sans cette attente, un hook-error publierait un déploiement GitHub vert sur une URL morte."""
    client = FakeClient([
        FakeResponse(link()),
        FakeResponse(listing(review_app_entry(git_ref="stale"))),
        FakeResponse(deployment()),
        FakeResponse(deployment(status)),
    ])

    with pytest.raises(RuntimeError, match=status):
        review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")


def test_wait_for_deployment_polls_until_the_build_leaves_the_pending_statuses(mocker):
    sleep = mocker.patch.object(review_app.time, "sleep")
    client = FakeClient([
        FakeResponse(deployment("building")),
        FakeResponse(deployment("starting")),
        FakeResponse(deployment("success")),
    ])

    review_app.wait_for_deployment(client, "jwt", "autometa-staging-pr42", "dep-1")

    assert len(client.calls) == 3
    assert sleep.call_count == 2


def test_wait_for_deployment_gives_up_loudly(mocker):
    mocker.patch.object(review_app.time, "sleep")
    mocker.patch.object(review_app.time, "monotonic", side_effect=[0.0, 10_000.0])
    client = FakeClient([FakeResponse(deployment("building"))])

    with pytest.raises(RuntimeError, match="building"):
        review_app.wait_for_deployment(client, "jwt", "autometa-staging-pr42", "dep-1")


def test_wait_for_addons_polls_until_every_addon_is_running(mocker):
    sleep = mocker.patch.object(review_app.time, "sleep")
    client = FakeClient([
        FakeResponse(addons()),
        FakeResponse(addons("provisioning", "running")),
        FakeResponse(addons("running", "running")),
    ])

    review_app.wait_for_addons(client, "jwt", "autometa-staging-pr42")

    assert len(client.calls) == 3
    assert sleep.call_count == 2


def test_wait_for_addons_gives_up_loudly(mocker):
    """Sans DATABASE_URL le postdeploy meurt : mieux vaut échouer ici qu'à l'intérieur du conteneur."""
    mocker.patch.object(review_app.time, "sleep")
    mocker.patch.object(review_app.time, "monotonic", side_effect=[0.0, 10_000.0])
    client = FakeClient([FakeResponse(addons("provisioning"))])

    with pytest.raises(RuntimeError, match="addons"):
        review_app.wait_for_addons(client, "jwt", "autometa-staging-pr42")


def test_stop_scales_the_web_containers_to_zero():
    """Scalingo ne réagit pas au passage en draft, et un collaborateur ne peut pas supprimer (401)."""
    client = FakeClient([FakeResponse(listing(review_app_entry())), FakeResponse({})])

    result = review_app.stop(client, "jwt", "autometa-staging", 42)

    assert result == {"action": "stopped", "app": "autometa-staging-pr42"}
    method, url, kwargs = client.calls[1]
    assert (method, url.rsplit("/v1", 1)[-1]) == ("POST", "/apps/autometa-staging-pr42/scale")
    assert kwargs["json"] == {"containers": [{"name": "web", "amount": 0}]}


def test_stop_is_a_noop_when_the_app_is_already_gone():
    client = FakeClient([FakeResponse(listing())])

    assert review_app.stop(client, "jwt", "autometa-staging", 42) == {"action": "absent", "app": None}
    assert len(client.calls) == 1


def test_stop_tolerates_a_404_from_scalingo():
    """Scalingo a pu détruire la review app entre le listing et le scale."""
    client = FakeClient([FakeResponse(listing(review_app_entry())), FakeResponse(status_code=404)])

    assert review_app.stop(client, "jwt", "autometa-staging", 42) == {
        "action": "absent",
        "app": "autometa-staging-pr42",
    }


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


def test_main_stop_does_not_require_a_sha(mocker, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("tk-us-secret\n"))
    mocker.patch.object(review_app.httpx, "Client", return_value=NullClient())
    mocker.patch.object(review_app, "exchange_token", return_value="jwt-bearer")
    stop = mocker.patch.object(review_app, "stop", return_value={"action": "absent", "app": None})

    assert review_app.main(["stop", "--app", "autometa-staging", "--pr", "42"]) == 0
    stop.assert_called_once()
    assert json.loads(capsys.readouterr().out)["action"] == "absent"


def test_main_rejects_ensure_without_sha(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("tk-us-secret\n"))

    with pytest.raises(SystemExit) as excinfo:
        review_app.main(["ensure", "--app", "autometa-staging", "--pr", "42"])

    assert excinfo.value.code == 2
