"""Tests for interactive file serving with S3 optimizations."""

from fastapi.testclient import TestClient

from web.app import app

client = TestClient(app)


def test_static_asset_redirects_to_presigned_url(mocker):
    mocker.patch.object(app.state, "_state", {}, create=True)
    mocker.patch("web.s3.interactive.exists", return_value=True)
    mocker.patch(
        "web.s3.interactive.get_url",
        return_value="https://s3.scw.com/bucket/app/style.css?Signature=xyz",
    )

    response = client.get("/interactive/app/style.css", follow_redirects=False)

    assert response.status_code == 307
    assert "s3.scw.com" in response.headers["Location"]
    assert response.headers["Cache-Control"] == "private, max-age=300"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_html_streamed_not_redirected(mocker):
    mocker.patch("web.app.list_variants", return_value=[])
    mocker.patch("web.s3.interactive.stream", return_value=iter([b"<html>ok</html>"]))

    response = client.get("/interactive/app/index.html")

    assert response.status_code == 200
    assert "Location" not in response.headers
    assert b"<html>ok</html>" in response.content


def test_missing_file_returns_404(mocker):
    mocker.patch("web.s3.interactive.exists", return_value=False)
    mocker.patch("web.s3.interactive.stream", return_value=None)

    response = client.get("/interactive/app/missing.html")

    assert response.status_code == 404


def test_python_files_blocked():
    response = client.get("/interactive/app/secret.py")

    assert response.status_code == 404


def test_path_traversal_blocked():
    response = client.get("/interactive/../../../etc/passwd")

    assert response.status_code == 404


def test_dirlike_path_redirects_to_trailing_slash(mocker):
    def exists(path):
        return path == "myapp/index.html"

    mocker.patch("web.s3.interactive.exists", side_effect=exists)
    response = client.get("/interactive/myapp", follow_redirects=False)
    assert response.status_code == 301
    assert response.headers["Location"] == "/interactive/myapp/"


def test_dirlike_path_with_no_index_returns_404(mocker):
    mocker.patch("web.s3.interactive.exists", return_value=False)
    mocker.patch("web.s3.interactive.stream", return_value=None)
    response = client.get("/interactive/no-such-app", follow_redirects=False)
    assert response.status_code == 404


def test_extensioned_path_is_not_treated_as_dir(mocker):
    """A path like /interactive/data.json must not be redirected even if data.json/index.html doesn't exist."""
    mocker.patch("web.s3.interactive.exists", return_value=False)
    mocker.patch("web.s3.interactive.stream", return_value=None)
    response = client.get("/interactive/data.json", follow_redirects=False)
    assert response.status_code == 404


def _variant(key, label="Bas-Rhin", token="00000000-0000-4000-8000-000000000067"):
    return {
        "key": key,
        "label": label,
        "token": token,
        "path": f"data/{token}.json",
        "url": f"/interactive/multi/?q={token}",
    }


def test_dod_3_index_without_q_lists_variants_and_links_to_edit_page(mocker):
    mocker.patch(
        "web.app.list_variants",
        return_value=[_variant("67"), _variant("68", "Haut-Rhin", "00000000-0000-4000-8000-000000000211")],
    )
    stream = mocker.patch("web.s3.interactive.stream")

    response = client.get("/interactive/multi/")

    assert response.status_code == 200
    assert "Bas-Rhin" in response.text and "Haut-Rhin" in response.text
    assert "<code>67</code>" in response.text
    assert 'href="/interactive/multi/?q=00000000-0000-4000-8000-000000000067"' in response.text
    assert 'href="/dashboards/multi/edit"' in response.text
    stream.assert_not_called()


def test_dod_1_redirect_to_the_trailing_slash_keeps_the_token(mocker):
    mocker.patch("web.s3.interactive.exists", return_value=True)

    response = client.get("/interactive/multi?q=00000000-0000-4000-8000-000000000067", follow_redirects=False)

    assert response.status_code == 301
    assert response.headers["Location"] == "/interactive/multi/?q=00000000-0000-4000-8000-000000000067"


def test_dod_3_index_with_q_serves_the_dashboard_page(mocker):
    listing = mocker.patch("web.app.list_variants", return_value=[_variant("67")])
    mocker.patch("web.s3.interactive.stream", return_value=iter([b"<html>tdb</html>"]))

    response = client.get("/interactive/multi/?q=00000000-0000-4000-8000-000000000067")

    assert response.status_code == 200
    assert b"<html>tdb</html>" in response.content
    listing.assert_not_called()


def test_dod_3_dashboard_without_variants_is_not_intercepted(mocker):
    mocker.patch("web.app.list_variants", return_value=[])
    mocker.patch("web.s3.interactive.stream", return_value=iter([b"<html>mono</html>"]))

    response = client.get("/interactive/mono/")

    assert b"<html>mono</html>" in response.content


def test_dod_3_only_the_index_is_intercepted(mocker):
    listing = mocker.patch("web.app.list_variants", return_value=[_variant("67")])
    mocker.patch("web.s3.interactive.stream", return_value=iter([b"{}"]))

    response = client.get("/interactive/multi/data/x.json")

    assert response.content == b"{}"
    listing.assert_not_called()


def test_dod_3_a_database_outage_does_not_take_the_dashboard_down(mocker):
    from sqlalchemy.exc import OperationalError

    mocker.patch("web.app.list_variants", side_effect=OperationalError("SELECT", {}, Exception("down")))
    mocker.patch("web.s3.interactive.stream", return_value=iter([b"<html>still up</html>"]))

    response = client.get("/interactive/multi/")

    assert b"<html>still up</html>" in response.content
