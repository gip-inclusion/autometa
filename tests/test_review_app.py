import importlib.util
from pathlib import Path

import httpx
import pytest

spec = importlib.util.spec_from_file_location("review_app", Path(__file__).parent.parent / "scripts" / "review_app.py")
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
