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
    method, url, kwargs = client.calls[0]
    assert (method, url) == ("POST", review_app.AUTH_URL)
    assert kwargs["auth"] == ("", "tk-us-secret")
    assert kwargs["timeout"] == review_app.TIMEOUT


def read_state(client):
    return review_app.find_review_app(client, "jwt", "autometa-staging", 42)


def deploy_app(client):
    return review_app.deploy_review_app(client, "jwt", "autometa-staging", 42)


def destroy_app(client):
    return review_app.destroy(client, "jwt", "autometa-staging", 42)


@pytest.mark.parametrize(
    ("operation", "responses"),
    [
        (read_state, [FakeResponse(listing())]),
        (deploy_app, [FakeResponse({})]),
        (destroy_app, [FakeResponse(listing(review_app_entry())), FakeResponse({})]),
    ],
    ids=["read_state", "deploy", "destroy"],
)
def test_scalingo_calls_carry_the_bearer_and_a_timeout(operation, responses):
    client = FakeClient(responses)

    operation(client)

    assert len(client.calls) == len(responses)
    for _, _, kwargs in client.calls:
        assert kwargs["headers"] == {"Authorization": "Bearer jwt"}
        assert kwargs["timeout"] == review_app.TIMEOUT


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

    method, url, kwargs = client.calls[1]
    assert method == "POST"
    assert url.endswith("/apps/autometa-staging/scm_repo_link/manual_review_app")
    assert kwargs["json"] == {"pull_request_id": 42}


def test_ensure_uses_the_app_name_returned_by_scalingo():
    client = FakeClient([FakeResponse(listing()), FakeResponse({"app_name": "autometa-staging-pr42-b7c1"})])

    result = review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")

    assert result["action"] == "created"
    assert result["app"] == "autometa-staging-pr42-b7c1"
    assert result["url"] == "https://autometa-staging-pr42-b7c1.osc-fr1.scalingo.io"


@pytest.mark.parametrize(
    "payload",
    [None, {}, {"id": "ra-1"}, ["autometa-staging-pr42"]],
    ids=["empty body", "no app_name", "other keys", "not an object"],
)
def test_ensure_falls_back_to_the_conventional_name(payload):
    client = FakeClient([FakeResponse(listing()), FakeResponse(payload)])

    result = review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")

    assert result["app"] == "autometa-staging-pr42"
    assert result["url"] == "https://autometa-staging-pr42.osc-fr1.scalingo.io"


def test_ensure_keeps_the_existing_app_name_over_the_post_response():
    listed = listing(review_app_entry(git_ref="staleref", app_name="autometa-staging-pr42-old"))
    client = FakeClient([FakeResponse(listed), FakeResponse({"app_name": "autometa-staging-pr42-new"})])

    result = review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")

    assert result == {
        "action": "updated",
        "app": "autometa-staging-pr42-old",
        "url": "https://autometa-staging-pr42-old.osc-fr1.scalingo.io",
    }


@pytest.mark.parametrize(
    "deployment",
    [
        None,
        {"id": "d-1", "status": "build-error", "git_ref": "abc123"},
        {"id": "d-1", "status": "hook-error", "git_ref": "abc123"},
    ],
)
def test_ensure_redeploys_unless_the_sha_is_successfully_deployed(deployment):
    entry = review_app_entry()
    entry["last_deployment"] = deployment
    client = FakeClient([FakeResponse(listing(entry)), FakeResponse()])

    result = review_app.ensure(client, "jwt", "autometa-staging", 42, "abc123")

    assert result["action"] == "updated"


def test_destroy_removes_the_review_app():
    client = FakeClient([FakeResponse(listing(review_app_entry())), FakeResponse()])

    result = review_app.destroy(client, "jwt", "autometa-staging", 42)

    assert result == {"action": "destroyed", "app": "autometa-staging-pr42"}
    method, url, kwargs = client.calls[1]
    assert method == "DELETE"
    assert url.endswith("/apps/autometa-staging-pr42")
    assert kwargs["params"] == {"current_name": "autometa-staging-pr42"}


def test_destroy_is_a_noop_when_already_gone():
    client = FakeClient([FakeResponse(listing())])

    result = review_app.destroy(client, "jwt", "autometa-staging", 42)

    assert result == {"action": "absent", "app": None}
    assert all(call[0] != "DELETE" for call in client.calls)


def test_destroy_tolerates_a_404_from_scalingo():
    client = FakeClient([FakeResponse(listing(review_app_entry())), FakeResponse(status_code=404)])

    result = review_app.destroy(client, "jwt", "autometa-staging", 42)

    assert result == {"action": "absent", "app": "autometa-staging-pr42"}


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
