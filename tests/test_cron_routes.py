"""Tests for cron route slug validation — guards against path-injection in downstream tempfile/S3 keys."""

import pytest

from web import cron


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


def test_view_script_s3_task(client, mocker):
    mocker.patch("web.routes.cron.find_task", return_value={"slug": "x", "source": "s3", "cron_path": "x/cron.py"})
    mocker.patch("web.routes.cron.read_cron_script", return_value="print('hi')")
    response = client.get("/api/cron/x/script")
    assert response.status_code == 200
    assert "print('hi')" in response.text


def test_view_script_missing_returns_404_not_500(client, mocker):
    mocker.patch("web.routes.cron.find_task", return_value={"slug": "x", "source": "s3", "cron_path": "x/cron.py"})
    mocker.patch("web.routes.cron.read_cron_script", return_value=None)
    response = client.get("/api/cron/x/script")
    assert response.status_code == 404


def test_read_cron_script_local(tmp_path):
    script = tmp_path / "cron.py"
    script.write_text("print('local')")
    assert cron.read_cron_script({"cron_path": str(script)}) == "print('local')"


def test_read_cron_script_s3(mocker):
    mocker.patch("web.cron.s3.interactive.download", return_value=b"print('s3')")
    assert cron.read_cron_script({"source": "s3", "cron_path": "x/cron.py"}) == "print('s3')"
