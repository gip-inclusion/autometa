"""Tests for interactive file serving with S3 optimizations."""

from fastapi.testclient import TestClient

from web.app import app

client = TestClient(app)


def test_static_asset_redirects_to_presigned_url(mocker):
    mocker.patch("web.s3.file_exists", return_value=True)
    mocker.patch(
        "web.s3.get_file_url",
        return_value="https://s3.scw.com/bucket/app/style.css?Signature=xyz",
    )

    response = client.get("/interactive/app/style.css", follow_redirects=False)

    assert response.status_code == 307
    assert "s3.scw.com" in response.headers["Location"]
    assert response.headers["Cache-Control"] == "private, max-age=300"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_html_streamed_not_redirected(mocker):
    mocker.patch("web.s3.stream_file", return_value=iter([b"<html>ok</html>"]))

    response = client.get("/interactive/app/index.html")

    assert response.status_code == 200
    assert "Location" not in response.headers
    assert b"<html>ok</html>" in response.content


def test_missing_file_returns_404(mocker):
    mocker.patch("web.s3.file_exists", return_value=False)
    mocker.patch("web.s3.stream_file", return_value=None)

    response = client.get("/interactive/app/missing.html")

    assert response.status_code == 404


def test_python_files_blocked():
    response = client.get("/interactive/app/secret.py")

    assert response.status_code == 404


def test_path_traversal_blocked():
    response = client.get("/interactive/../../../etc/passwd")

    assert response.status_code == 404
