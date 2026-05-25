"""Tests for cron route slug validation — guards against path-injection in downstream tempfile/S3 keys."""

import pytest


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/api/cron/{slug}/run"),
        ("post", "/api/cron/{slug}/toggle"),
        ("get", "/api/cron/{slug}/script"),
        ("get", "/api/cron/{slug}/logs"),
    ],
)
@pytest.mark.parametrize(
    "bad_slug",
    [
        "foo..bar",
        "UPPER",
        "with.dot",
        "with$dollar",
        "with%20encoded",
        "a" * 101,
    ],
)
def test_invalid_slug_rejected(client, method, path, bad_slug):
    response = getattr(client, method)(path.format(slug=bad_slug))
    assert response.status_code == 422


def test_valid_slug_reaches_handler(client, mocker):
    mocker.patch("web.routes.cron.find_task", return_value=None)
    response = client.get("/api/cron/check-s3-backups/script")
    assert response.status_code == 404
    assert response.json() == {"error": "Task not found"}
