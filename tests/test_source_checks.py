"""Sondes de sources — web/source_checks.py."""

import httpx
import pytest

from lib.query import QueryResult as QueryOutcome
from web import source_checks
from web.source_checks import (
    check_app_db,
    check_autometa_tables,
    check_dashboard_storage,
    check_data_inclusion,
    check_datadog,
    check_grist,
    check_livestorm,
    check_matomo,
    check_metabase_instance,
    check_notion,
    check_rpe,
    check_s3,
    check_slack,
    check_tally,
    check_zendesk,
)


def fake_response(status=200, payload=None):
    request = httpx.Request("GET", "https://exemple.test/")
    return httpx.Response(status, json=payload if payload is not None else {}, request=request)


@pytest.fixture(autouse=True)
def stub_credentials(mocker):
    """Aucune sonde ne doit dépendre de credentials : `get_source_config` résout ${env.VAR} en mode strict."""
    mocker.patch.object(
        source_checks,
        "get_source_config",
        side_effect=lambda source_type, instance=None: {
            "url": "https://exemple.test",
            "subdomain": "exemple",
            "email": "essai@exemple.test",
            "token": "factice",
        },
    )
    mocker.patch.object(
        source_checks, "get_matomo", return_value=mocker.MagicMock(url="matomo.exemple.test", token="factice")
    )


HTTP_PROBES = [
    (check_notion, "get", {"name": "Autometa"}, "intégration : Autometa"),
    (check_tally, "get", {}, "joignable"),
    (
        check_datadog,
        "post",
        {"data": {"buckets": [{"computes": {"c0": 42}}]}},
        "42 événements sur la dernière minute",
    ),
    (check_grist, "get", {"tables": [{"id": "a"}, {"id": "b"}]}, "2 tables"),
    (check_livestorm, "get", {}, "joignable"),
    (check_slack, "head", {}, "API joignable"),
    (check_zendesk, "get", {"view_count": {"value": 12}}, "12 vues"),
]


@pytest.mark.parametrize(
    ("probe", "verb", "payload", "expected"), HTTP_PROBES, ids=lambda v: getattr(v, "__name__", None)
)
def test_http_probe_reports_success(mocker, probe, verb, payload, expected):
    mocker.patch.object(httpx, verb, return_value=fake_response(200, payload))
    assert probe() == (True, expected)


@pytest.mark.parametrize(
    ("probe", "verb", "payload", "expected"), HTTP_PROBES, ids=lambda v: getattr(v, "__name__", None)
)
def test_http_probe_reports_the_status_code_on_failure(mocker, probe, verb, payload, expected):
    mocker.patch.object(httpx, verb, return_value=fake_response(503))
    assert probe() == (False, "HTTP 503")


def test_zendesk_stays_reachable_when_the_count_is_missing(mocker):
    """Le format de la réponse a déjà changé : ne pas afficher « ? vues »."""
    mocker.patch.object(httpx, "get", return_value=fake_response(200, {}))
    assert check_zendesk() == (True, "joignable")


@pytest.mark.parametrize(
    ("status", "expected"),
    [(200, (True, "en bonne santé")), (502, (False, "HTTP 502"))],
)
def test_check_metabase_instance(mocker, status, expected):
    mocker.patch.object(httpx, "get", return_value=fake_response(status))
    assert check_metabase_instance("stats") == expected


def test_check_matomo_returns_the_version(mocker):
    mocker.patch.object(httpx, "get", return_value=fake_response(200, {"value": "5.8.0"}))
    assert check_matomo() == (True, "v5.8.0")


def test_check_matomo_raises_on_http_error_so_the_caller_redacts_it(mocker):
    """La sonde laisse remonter l'exception httpx — dont l'URL porte le jeton, d'où la rédaction en amont."""
    mocker.patch.object(httpx, "get", return_value=fake_response(500))
    with pytest.raises(httpx.HTTPStatusError):
        check_matomo()


@pytest.mark.parametrize(
    ("probe", "target", "expected"),
    [
        (check_autometa_tables, "execute_autometa_tables_query", "connectée (12 ms)"),
        (check_data_inclusion, "execute_data_inclusion_query", "connectée (12 ms)"),
    ],
    ids=["autometa_tables", "data_inclusion"],
)
def test_sql_probe_reports_success(mocker, probe, target, expected):
    mocker.patch.object(source_checks, target, return_value=QueryOutcome(success=True, data={}, execution_time_ms=12))
    assert probe() == (True, expected)


@pytest.mark.parametrize(
    ("probe", "target"),
    [
        (check_autometa_tables, "execute_autometa_tables_query"),
        (check_data_inclusion, "execute_data_inclusion_query"),
        (check_dashboard_storage, "execute_dashboard_storage_query"),
    ],
    ids=["autometa_tables", "data_inclusion", "dashboard_storage"],
)
def test_sql_probe_surfaces_the_error(mocker, probe, target):
    mocker.patch.object(
        source_checks, target, return_value=QueryOutcome(success=False, data=None, error="connexion refusée")
    )
    assert probe() == (False, "connexion refusée")


def test_check_dashboard_storage_counts_tables(mocker):
    mocker.patch.object(
        source_checks,
        "execute_dashboard_storage_query",
        return_value=QueryOutcome(success=True, data={"columns": ["count"], "rows": [[7]], "row_count": 1}),
    )
    assert check_dashboard_storage() == (True, "7 tables")


@pytest.mark.integration
def test_check_app_db_against_a_real_database():
    assert check_app_db() == (True, "connectée")


def test_check_rpe_summarizes_passing_contract(mocker):
    mocker.patch(
        "web.source_checks.doctor",
        return_value={
            "ok": True,
            "checks": [
                {"check": "tls", "ok": True, "reason": "TLS OK"},
                {"check": "getcuberesult", "ok": True, "reason": "19 valeurs"},
            ],
        },
    )
    ok, detail = check_rpe()
    assert ok is True
    assert detail == "tls · getcuberesult OK"


def test_check_rpe_surfaces_first_failing_check(mocker):
    mocker.patch(
        "web.source_checks.doctor",
        return_value={
            "ok": False,
            "checks": [
                {"check": "tls", "ok": True, "reason": "TLS OK"},
                {"check": "login", "ok": False, "reason": "login refusé"},
            ],
        },
    )
    ok, detail = check_rpe()
    assert ok is False
    assert detail == "login : login refusé"


FAUX = "valeur-factice-de-test"  # gitleaks:allow


@pytest.mark.parametrize(
    "template",
    [
        # httpx met l'URL complète dans ses exceptions, et check_matomo passe le jeton en paramètre.
        "Server error '500' for url 'https://matomo/index.php?module=API&token_auth={v}'",
        "HTTP 401 sur https://x/api?api_key={v}&format=json",
        "échec https://y/?password={v}",
        "postgresql://u:{v}@host/db",
    ],
)
def test_probe_details_never_carry_a_secret(template):
    from web.source_checks import redact

    assert FAUX not in redact(template.format(v=FAUX))


@pytest.mark.parametrize(
    ("upload", "download", "expect_ok", "detail_substr"),
    [
        (True, b"ping", True, "écriture/lecture/suppression OK"),
        (False, None, False, "écriture refusée"),
        (True, b"nope", False, "relecture incohérente"),
    ],
)
def test_check_s3_roundtrip(mocker, upload, download, expect_ok, detail_substr):
    interactive = mocker.patch("web.source_checks.s3.interactive")
    interactive.upload.return_value = upload
    interactive.download.return_value = download

    ok, detail = check_s3()

    assert ok is expect_ok
    assert detail_substr in detail
    if expect_ok:
        interactive.delete.assert_called_once_with("selftest/ping.txt")
