"""Tests for the Tag Manager audit dashboard routes."""

import pytest

from lib.query import QueryResult

SITES = [
    {"name": "Emplois", "matomo_id": 117, "container_id": "TlN6Ou1K"},
    {"name": "Marché", "matomo_id": 136, "container_id": "RBvmJtrU"},
]

CONTAINER = {
    "draft": {"idcontainerversion": 50},
    "releases": [
        {"environment": "live", "idcontainerversion": 42},
        {"environment": "staging", "idcontainerversion": 41},
    ],
}

EXPORT = {
    "triggers": [
        {"idtrigger": 1, "name": "All pages", "type": "PageView", "conditions": []},
        {"idtrigger": 2, "name": "Click CTA", "type": "Click", "conditions": []},
    ],
    "tags": [
        {"idtag": 10, "name": "Matomo PageView", "type": "Matomo", "fire_trigger_ids": [1]},
        {"idtag": 11, "name": "Form submit", "type": "CustomHtml", "fire_trigger_ids": [2]},
    ],
}


@pytest.fixture
def mock_matomo(mocker):
    mocker.patch("web.routes.tag_manager.get_tag_manager_sites", return_value=SITES)

    def respond(instance, caller, method, params, **_kw):
        if method == "TagManager.getContainer":
            return QueryResult(success=True, data=CONTAINER)
        if method == "TagManager.exportContainerVersion":
            return QueryResult(success=True, data=EXPORT)
        raise AssertionError(f"unexpected method {method}")

    return mocker.patch("web.routes.tag_manager.execute_matomo_query", side_effect=respond)


def _auth():
    return {"X-Forwarded-Email": "test@example.com"}


@pytest.mark.parametrize(
    "path,stack,must_contain",
    [
        ("/tag-manager", "sites", ["Emplois", "Marché"]),
        ("/tag-manager/sites/117", "triggers", ["All pages", "Click CTA"]),
        ("/tag-manager/sites/117/triggers/1", "tags", ["All pages", "Matomo PageView"]),
    ],
)
def test_permalinks_render_full_page_with_correct_stack(client, mock_matomo, path, stack, must_contain):
    response = client.get(path, headers=_auth())
    assert response.status_code == 200
    body = response.text
    assert f'data-stack="{stack}"' in body
    for needle in must_contain:
        assert needle in body


@pytest.mark.parametrize(
    "trigger_id,expected,not_expected",
    [
        (1, "Matomo PageView", "Form submit"),
        (2, "Form submit", "Matomo PageView"),
    ],
)
def test_tags_filtered_by_trigger(client, mock_matomo, trigger_id, expected, not_expected):
    response = client.get(f"/tag-manager/sites/117/triggers/{trigger_id}", headers=_auth())
    assert response.status_code == 200
    assert expected in response.text
    assert not_expected not in response.text


def test_unknown_site_returns_404(client, mock_matomo):
    response = client.get("/tag-manager/sites/999", headers=_auth())
    assert response.status_code == 404


def test_no_live_release_renders_empty_message(client, mocker):
    mocker.patch("web.routes.tag_manager.get_tag_manager_sites", return_value=SITES)
    container_no_live = {"draft": {"idcontainerversion": 50}, "releases": []}
    mocker.patch(
        "web.routes.tag_manager.execute_matomo_query",
        return_value=QueryResult(success=True, data=container_no_live),
    )
    response = client.get("/tag-manager/sites/117", headers=_auth())
    assert response.status_code == 200
    assert "Aucune version publiée" in response.text


def test_matomo_error_returns_generic_message_no_secret_leak(client, mocker):
    mocker.patch("web.routes.tag_manager.get_tag_manager_sites", return_value=SITES)
    mocker.patch(
        "web.routes.tag_manager.execute_matomo_query",
        return_value=QueryResult(success=False, data=None, error="Bearer token leaked: secret-xyz"),
    )
    response = client.get("/tag-manager/sites/117", headers=_auth())
    assert response.status_code == 502
    assert "secret-xyz" not in response.text
    assert "Traceback" not in response.text


def test_route_does_not_instantiate_matomo_api(client, mocker):
    api_ctor = mocker.patch("lib.matomo.MatomoAPI.__init__", side_effect=AssertionError("direct instantiation"))
    mocker.patch("web.routes.tag_manager.get_tag_manager_sites", return_value=SITES)
    mocker.patch(
        "web.routes.tag_manager.execute_matomo_query",
        return_value=QueryResult(success=True, data=CONTAINER),
    )
    client.get("/tag-manager/sites/117", headers=_auth())
    api_ctor.assert_not_called()
