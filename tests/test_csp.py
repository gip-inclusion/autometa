"""CSP bloquante des pages de TDB, et collecte des violations."""

import json
import logging

import pytest
from fastapi.testclient import TestClient

from web.app import app

client = TestClient(app)


def csp_report(**fields):
    return json.dumps({"csp-report": fields})


def test_interactive_page_carries_blocking_policy(mocker):
    mocker.patch("web.app.list_variants", return_value=[])
    mocker.patch("web.s3.interactive.stream", return_value=iter([b"<html>ok</html>"]))
    mocker.patch("web.config.S3_ENDPOINT", "https://s3.fr-par.scw.cloud")
    mocker.patch("web.config.S3_BUCKET", "autometa")

    response = client.get("/interactive/app/index.html")

    policy = response.headers["Content-Security-Policy"]
    assert "Content-Security-Policy-Report-Only" not in response.headers
    assert policy == (
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net/npm/ https://unpkg.com https://d3js.org"
        " https://matomo.inclusion.gouv.fr https://autometa.s3.fr-par.scw.cloud;"
        " object-src 'none'; base-uri 'self'; report-uri /api/csp-report"
    )


@pytest.mark.parametrize("endpoint, bucket", [(None, "autometa"), ("https://s3.fr-par.scw.cloud", None)])
def test_policy_omits_s3_when_endpoint_or_bucket_is_unset(endpoint, bucket, mocker):
    mocker.patch("web.config.S3_ENDPOINT", endpoint)
    mocker.patch("web.config.S3_BUCKET", bucket)
    mocker.patch("web.s3.interactive.exists", return_value=False)
    mocker.patch("web.s3.interactive.stream", return_value=None)

    response = client.get("/interactive/app/missing.html")

    assert response.headers["Content-Security-Policy"].startswith(
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net/npm/ https://unpkg.com https://d3js.org"
        " https://matomo.inclusion.gouv.fr; "
    )


def test_application_pages_carry_no_policy():
    response = client.get("/api/auth/status")

    assert "Content-Security-Policy" not in response.headers


def test_violation_is_logged_without_query_string(caplog):
    caplog.set_level(logging.WARNING, logger="web.csp")
    body = csp_report(**{
        "document-uri": "https://autometa.example/interactive/tdb-mayotte/?q=secret-token",
        "effective-directive": "script-src-elem",
        "blocked-uri": "https://evil.example/lib.js?k=v",
        "source-file": "https://autometa.example/interactive/tdb-mayotte/?q=secret-token",
    })

    response = client.post("/api/csp-report", content=body, headers={"Content-Type": "application/csp-report"})

    assert response.status_code == 204
    assert caplog.messages == [
        "Violation CSP TDB=tdb-mayotte directive=script-src-elem bloqué=https://evil.example/lib.js"
        " source=https://autometa.example/interactive/tdb-mayotte/"
    ]
    assert "secret-token" not in caplog.text


def test_inline_violation_keeps_keyword_and_falls_back_to_violated_directive(caplog):
    caplog.set_level(logging.WARNING, logger="web.csp")
    body = csp_report(**{
        "document-uri": "https://autometa.example/interactive/annuairepro/",
        "violated-directive": "script-src",
        "blocked-uri": "inline",
    })

    client.post("/api/csp-report", content=body)

    assert caplog.messages == ["Violation CSP TDB=annuairepro directive=script-src bloqué=inline source="]


@pytest.mark.parametrize("body", ["not json", "[]", json.dumps({"autre": {}})])
def test_unreadable_report_is_rejected(body, caplog):
    caplog.set_level(logging.WARNING, logger="web.csp")

    response = client.post("/api/csp-report", content=body)

    assert response.status_code == 400
    assert caplog.messages == []
