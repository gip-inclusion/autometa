"""Tests for lib/rpe.py — sel building, response parsing, period resolution, and live RPE access."""

import json
import ssl

import httpx
import pytest
from cryptography import x509

from lib import rpe

DATASET = "Accès et présence en emploi"


def test_rpe_ca_file_is_the_sectigo_ev_r36_intermediate():
    cert = x509.load_pem_x509_certificate(rpe.RPE_CA_FILE.read_bytes())
    assert "Sectigo Public Server Authentication CA EV R36" in cert.subject.rfc4514_string()
    assert "R46" in cert.issuer.rfc4514_string()  # signé par la racine déjà présente dans certifi


def test_build_ssl_context_trusts_the_embedded_intermediate():
    ctx = rpe.build_ssl_context()
    assert isinstance(ctx, ssl.SSLContext)
    assert any("EV R36" in str(c["subject"]) for c in ctx.get_ca_certs())


def test_http_client_applies_user_agent_and_shared_ssl_context():
    client = rpe.http_client()
    assert client.headers["User-Agent"] == rpe.UA
    assert client.timeout.read == rpe.TIMEOUT
    client.close()


@pytest.mark.parametrize("timeout,cookies", [(5, {"JSESSIONID": "abc"}), (rpe.TIMEOUT, None)])
def test_http_client_passes_timeout_and_cookies(timeout, cookies):
    client = rpe.http_client(timeout=timeout, cookies=cookies)
    assert client.timeout.read == timeout
    if cookies:
        assert client.cookies.get("JSESSIONID") == "abc"
    client.close()


@pytest.mark.parametrize(
    "exc,fragment",
    [
        (httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer"), "chaîne TLS invalide"),
        (httpx.ConnectError("Connection refused"), "connexion impossible"),
        (httpx.ConnectTimeout("timed out"), "serveur injoignable"),
    ],
)
def test_check_tls_reports_specific_reason_on_failure(mocker, exc, fragment):
    client = mocker.MagicMock()
    client.__enter__ = mocker.MagicMock(return_value=client)
    client.__exit__ = mocker.MagicMock(return_value=False)
    client.get.side_effect = exc
    mocker.patch.object(rpe, "http_client", return_value=client)
    ok, reason = rpe.check_tls()
    assert ok is False
    assert fragment in reason


def test_doctor_short_circuits_on_tls_failure(mocker):
    mocker.patch.object(rpe, "check_tls", return_value=(False, "chaîne TLS invalide (…)"))
    connect = mocker.patch.object(rpe.RpeClient, "connect")
    result = rpe.doctor()
    assert result["ok"] is False
    assert result["checks"] == [{"check": "tls", "ok": False, "reason": "chaîne TLS invalide (…)"}]
    connect.assert_not_called()  # pas de login tant que la couche TLS est cassée


def test_doctor_short_circuits_on_login_failure(mocker):
    mocker.patch.object(rpe, "check_tls", return_value=(True, "TLS OK"))
    mocker.patch.object(rpe, "check_connectivity", return_value=(False, "login refusé (signatures GWT périmées ?)"))
    connect = mocker.patch.object(rpe.RpeClient, "connect")
    result = rpe.doctor()
    assert result["ok"] is False
    assert [c["check"] for c in result["checks"]] == ["tls", "login"]
    connect.assert_not_called()


def test_doctor_reports_empty_flowsview(mocker):
    mocker.patch.object(rpe, "check_tls", return_value=(True, "TLS OK"))
    mocker.patch.object(rpe, "check_connectivity", return_value=(True, "login OK"))
    client = mocker.MagicMock()
    client.refresh_catalog.return_value = ({}, "flows")
    mocker.patch.object(rpe.RpeClient, "connect", return_value=client)
    result = rpe.doctor()
    assert result["ok"] is False
    assert [c["check"] for c in result["checks"]] == ["tls", "login", "flowsview"]
    client.close.assert_called_once()


def test_doctor_all_green(mocker):
    mocker.patch.object(rpe, "check_tls", return_value=(True, "TLS OK"))
    mocker.patch.object(rpe, "check_connectivity", return_value=(True, "login OK"))
    client = mocker.MagicMock()
    client.refresh_catalog.return_value = ({"CK": "CUBEID"}, "flows-response")
    client.query.return_value = [{"measure_id": "M", "value": 0.4}]
    mocker.patch.object(rpe.RpeClient, "connect", return_value=client)
    mocker.patch.object(
        rpe, "parse_charts", return_value=[{"cube_key": "CK", "measures_shown": ["M"], "dims_shown": []}]
    )
    result = rpe.doctor()
    assert result["ok"] is True
    assert [c["check"] for c in result["checks"]] == ["tls", "login", "flowsview", "getcuberesult"]


def test_probe_getcuberesult_accepts_recognized_values(mocker):
    client = mocker.MagicMock()
    client.query.return_value = [{"measure_id": "M", "value": 0.4}, {"measure_id": None, "value": 1.0}]
    charts = [{"cube_key": "CK", "measures_shown": ["Mlabel"], "dims_shown": []}]
    ok, reason = rpe._probe_getcuberesult(client, charts, {"CK": "CUBEID"})
    assert ok is True
    assert "valeurs reconnues" in reason


def test_probe_getcuberesult_rejects_presence_fallback(mocker):
    client = mocker.MagicMock()
    client.query.return_value = [{"measure_id": None, "value": 1.0}]  # repli présence = mesure non reconnue
    charts = [{"cube_key": "CK", "measures_shown": ["Mlabel"], "dims_shown": []}]
    ok, reason = rpe._probe_getcuberesult(client, charts, {"CK": "CUBEID"})
    assert ok is False
    assert "getCubeResult changé" in reason


def test_probe_getcuberesult_skips_cubes_without_cubeid(mocker):
    client = mocker.MagicMock()
    client.query.return_value = [{"measure_id": "M", "value": 0.4}]
    charts = [
        {"cube_key": "NOPE", "measures_shown": ["M"], "dims_shown": []},
        {"cube_key": "CK", "measures_shown": ["M"], "dims_shown": []},
    ]
    ok, _ = rpe._probe_getcuberesult(client, charts, {"CK": "CUBEID"})
    assert ok is True
    assert client.query.call_count == 1  # n'interroge que le cube doté d'un cubeId


def make_body(dim_axes, lines, headers, measures):
    return {
        "dimsAndMeasuresHeaders": headers,
        "axis": [measures, *dim_axes],
        "lines": lines,
    }


@pytest.mark.integration
def test_signature_roundtrip():
    rpe.ensure_schema()
    rpe.store_signature(rpe.Signatures("P", "S", "L", "D", "PASS"), sid="SID", jsessionid="J", bundle_nocache="n.js")
    row = rpe.load_signature_row()
    assert row["permutation"] == "P" and row["strong_name"] == "S" and row["sid"] == "SID"


def test_load_signatures_prefers_db_then_env(mocker):
    mocker.patch("web.config.RPE_PERMUTATION", "ENVPERM")
    mocker.patch("web.config.RPE_STRONG_NAME", "ENVSTRONG")
    mocker.patch("web.config.RPE_POLICY_LOGIN", "ENVL")
    mocker.patch("web.config.RPE_POLICY_DASH", "ENVD")
    mocker.patch("web.config.RPE_PUBLIC_PASS", "PASS")

    mocker.patch.object(rpe, "load_signature_row", return_value=None)
    env_sig = rpe.load_signatures()
    assert (
        env_sig.permutation,
        env_sig.strong_name,
        env_sig.policy_login,
        env_sig.policy_dash,
        env_sig.public_pass,
    ) == ("ENVPERM", "ENVSTRONG", "ENVL", "ENVD", "PASS")

    mocker.patch.object(
        rpe,
        "load_signature_row",
        return_value={
            "permutation": "DBPERM",
            "strong_name": "DBSTRONG",
            "policy_login": "DBL",
            "policy_dash": "DBD",
        },
    )
    db_sig = rpe.load_signatures()
    assert db_sig.permutation == "DBPERM" and db_sig.strong_name == "DBSTRONG"
    assert db_sig.public_pass == "PASS"  # password always from env (public value)


def test_render_gwt_fills_all_placeholders():
    from lib import rpe_gwt

    out = rpe_gwt.render_gwt(
        "__STRONG_NAME__|__POLICY_LOGIN__|__POLICY_DASH__|__RPE_PASS__",
        strong_name="S",
        policy_login="L",
        policy_dash="D",
        public_pass="P",
    )
    assert out == "S|L|D|P"


def test_gwt_templates_have_no_baked_hashes():
    from lib import rpe_gwt

    for payload in rpe_gwt.GWT.values():
        assert "B28E527AF46D9C6155A876F4769EC2F4" not in payload
        assert "__STRONG_NAME__" in payload


def test_parse_single_dim():
    body = make_body(
        dim_axes=[[{"p": 0, "i": "84", "f": "AUVERGNE-RHÔNE-ALPES"}, {"p": 1, "i": "53", "f": "BRETAGNE"}]],
        lines=[[0, 0, 0.41], [0, 1, 0.40]],
        headers=["Région", "Accès à l'emploi à 6 mois"],
        measures=[{"p": 0, "m": 0, "i": "M_ID", "f": "Accès à l'emploi à 6 mois"}],
    )
    rows = rpe.RpeClient._parse(DATASET, {}, body, ndims=1)
    assert [r["member_label"] for r in rows] == ["AUVERGNE-RHÔNE-ALPES", "BRETAGNE"]
    assert rows[0] == {
        "dataset": DATASET,
        "measure": "Accès à l'emploi à 6 mois",
        "measure_id": "M_ID",
        "value": 0.41,
        "Région": "AUVERGNE-RHÔNE-ALPES",
        "Région_code": "84",
        "dimension": "Région",
        "member_code": "84",
        "member_label": "AUVERGNE-RHÔNE-ALPES",
        "period": None,
    }


def test_parse_multi_dim_keeps_both_dimensions():
    body = make_body(
        dim_axes=[
            [{"p": 0, "i": "84", "f": "AUVERGNE-RHÔNE-ALPES"}],
            [{"p": 0, "i": "Hommes"}, {"p": 1, "i": "Femmes"}],
        ],
        lines=[[0, 0, 0, 0.39], [0, 0, 1, 0.31]],
        headers=["Région", "Sexe", "Accès"],
        measures=[{"p": 0, "m": 0, "i": "M_ID", "f": "Accès"}],
    )
    rows = rpe.RpeClient._parse(DATASET, {}, body, ndims=2)
    assert len(rows) == 2
    assert rows[0]["Région"] == "AUVERGNE-RHÔNE-ALPES" and rows[0]["Sexe"] == "Hommes"
    assert rows[1]["Sexe"] == "Femmes" and rows[1]["value"] == 0.31


@pytest.mark.parametrize(
    "breakdown,sel,expected",
    [
        ("Date d'observation", {}, "sept. 2025"),
        ("Région", {"dimsToFilter": [{"dim": "D_DATETAETPED", "selectedMembers": [1756677600]}]}, "2025-09"),
        ("Région", {}, None),
    ],
)
def test_period_of(breakdown, sel, expected):
    member = {"f": "sept. 2025"} if "ate" in breakdown else {"f": "BRETAGNE"}
    assert rpe.period_of(sel, breakdown, member) == expected


def test_epoch_month():
    assert rpe.epoch_month(1756677600 + 43200) == "2025-09"


def test_query_builds_multidim_sel_and_parses(mocker):
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    client.sid = "sid"
    name = DATASET
    client.catalog = {"CK1": {"cubeName": name, "dimensions": [], "measures": [{"id": "MID", "label": "M"}]}}
    client.cubeids = {"CK1": "CUBEID"}

    captured = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        captured["params"] = data
        resp = mocker.MagicMock(status_code=200)
        resp.raise_for_status = lambda: None
        resp.json = lambda: make_body(
            [[{"p": 0, "i": "84", "f": "ARA"}], [{"p": 0, "i": "Hommes"}]],
            [[0, 0, 0, 1.5]],
            ["Région", "Sexe", "M"],
            [{"p": 0, "m": 0, "i": "MID", "f": "M"}],
        )
        return resp

    client.http = mocker.MagicMock()
    client.http.post.side_effect = fake_post

    rows = client.query(name, [{"dim": "C_TERRITOIRE_ID", "hPos": 0, "lPos": 1}, "C_LBLSEXE"], ["MID"])

    sel = json.loads(captured["params"]["sel"])
    assert sel["axis"] == [None, [0], [1]]
    assert sel["pivot"] == 0
    assert sel["measuresToKeep"] == ["MID"]
    assert [d["dim"] for d in sel["dimsToExplore"]] == ["C_TERRITOIRE_ID", "C_LBLSEXE"]
    assert captured["params"]["cubeid"] == "CUBEID"
    assert rows[0]["Région"] == "ARA" and rows[0]["Sexe"] == "Hommes" and rows[0]["value"] == 1.5


def test_query_raises_without_cubeid(mocker):
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    client.sid = "sid"
    client.catalog = {"CK1": {"cubeName": DATASET, "dimensions": [], "measures": []}}
    client.cubeids = {}
    client.http = mocker.MagicMock()
    with pytest.raises(rpe.RpeLoginError):
        client.query(DATASET, ["C_LBLSEXE"], ["MID"])


def test_query_rejects_server_side_geo_filter(mocker):
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    client.sid = "sid"
    client.catalog = {"CK1": {"cubeName": DATASET, "dimensions": [], "measures": [{"id": "MID", "label": "M"}]}}
    client.cubeids = {"CK1": "CUBEID"}
    client.http = mocker.MagicMock()
    with pytest.raises(ValueError, match="territory"):
        client.query(DATASET, ["C_LBLSEXE"], ["MID"], filters={"C_TERRITOIRE_ID": ["11"]})
    client.http.post.assert_not_called()


@pytest.mark.parametrize("palier,expected_level", [("Région", 1), ("Département", 0), ("CLPE", -1)])
def test_query_territory_filter_uses_palier_level(mocker, palier, expected_level):
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    client.sid = "sid"
    client.catalog = {"CK1": {"cubeName": DATASET, "dimensions": [], "measures": [{"id": "MID", "label": "M"}]}}
    client.cubeids = {"CK1": "CUBEID"}
    captured = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        captured["params"] = data
        resp = mocker.MagicMock(status_code=200)
        resp.raise_for_status = lambda: None
        resp.json = lambda: make_body(
            [[{"p": 0, "i": "78", "f": "YVELINES"}]],
            [[0, 0, 0.78]],
            ["Territoire", "M"],
            [{"p": 0, "m": 0, "i": "MID", "f": "M"}],
        )
        return resp

    client.http = mocker.MagicMock()
    client.http.post.side_effect = fake_post

    client.query(DATASET, ["D_DATESATISACCO"], ["MID"], territory=(palier, ["78"]))

    sel = json.loads(captured["params"]["sel"])
    assert sel["dimsToFilter"] == [
        {"dim": "C_TERRITOIRE_ID", "hierarchy": 0, "level": expected_level, "selectedMembers": ["78"], "mode": 0}
    ]


def test_connect_reuses_cached_session(mocker):
    mocker.patch.object(rpe, "load_signatures", return_value=rpe.Signatures("P", "S", "L", "D", "PASS"))
    mocker.patch.object(
        rpe,
        "load_signature_row",
        return_value={
            "jsessionid": "JS123",
            "sid": "SID456",
            "validated_at": rpe.datetime.now(rpe.timezone.utc),
        },
    )
    login_spy = mocker.patch("lib.rpe.login", side_effect=AssertionError("ne doit pas se reconnecter"))
    mocker.patch.object(rpe.RpeClient, "_load_catalog", return_value={})
    mocker.patch.object(rpe.RpeClient, "_load_cubeids", return_value={})
    c = rpe.RpeClient.connect()
    assert c.sid == "SID456"
    assert c.http.cookies.get("JSESSIONID") == "JS123"
    login_spy.assert_not_called()


def test_post_file_relogins_on_403(mocker):
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    client.sid = "SID"
    r403 = mocker.MagicMock(status_code=403)
    r200 = mocker.MagicMock(status_code=200)
    r200.raise_for_status = lambda: None
    client.http = mocker.MagicMock()
    client.http.post.side_effect = [r403, r200]
    relogin = mocker.patch.object(rpe.RpeClient, "_relogin")
    out = client._post_file({"method": "getCubeResult"})
    assert out is r200
    relogin.assert_called_once()


def test_cli_apply_where_filters_rows():
    import importlib.util
    import pathlib

    path = pathlib.Path(__file__).parent.parent / "skills/rpe/scripts/query.py"
    spec = importlib.util.spec_from_file_location("rpe_query_cli", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    rows = [{"Région_code": "11", "v": 1}, {"Région_code": "84", "v": 2}, {"Région_code": "11", "v": 3}]
    assert mod.apply_where(rows, ["Région_code=11"]) == [{"Région_code": "11", "v": 1}, {"Région_code": "11", "v": 3}]
    assert mod.apply_where(rows, []) == rows

    measures = [{"id": "Entrant en formation (switch)", "label": "Entrées"}, {"id": "X9F022", "label": "Accès"}]
    assert mod.grep(measures, "entrant") == [measures[0]]
    assert mod.grep(measures, None) == measures

    assert mod.parse_ddvar("0") == 0 and mod.parse_ddvar("-3") == -3  # numérique → int
    assert mod.parse_ddvar("Mensuel") == "Mensuel"  # non numérique → chaîne brute (pas de crash)

    assert mod.parse_territory([]) is None
    assert mod.parse_territory(["78:dept"]) == ("Département", ["78"])
    assert mod.parse_territory(["11:region"]) == ("Région", ["11"])
    assert mod.parse_territory(["CLPE78001:cle"]) == ("CLPE", ["CLPE78001"])
    assert mod.parse_territory(["78:dept", "92:dept"]) == ("Département", ["78", "92"])
    with pytest.raises(SystemExit):
        mod.parse_territory(["78"])  # palier manquant
    with pytest.raises(SystemExit):
        mod.parse_territory(["78:bidon"])  # palier inconnu
    with pytest.raises(SystemExit):
        mod.parse_territory(["78:dept", "11:region"])  # paliers mélangés


def test_refresh_alerts_and_reraises_on_login_failure(mocker):
    mocker.patch.object(rpe, "ensure_schema")
    mocker.patch.object(rpe.RpeClient, "connect", side_effect=rpe.RpeLoginError("boom"))
    alert = mocker.patch.object(rpe, "notify_alert_channel")
    with pytest.raises(rpe.RpeLoginError):
        rpe.refresh()
    alert.assert_called_once()


def test_norm_unifies_apostrophes_case_space():
    assert rpe.norm("Part  des  RECOURS ’X") == "part des recours 'x"


def test_resolve_measures_tolerates_apostrophe_and_label(mocker):
    cat = [{"id": "Part des recours avec offre d’emploi (Switch %)", "label": "Part des recours avec offre d’emploi"}]
    mocker.patch.object(rpe.RpeClient, "measures", return_value=cat)
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    exact = cat[0]["id"]
    assert client._resolve_measures("ds", [exact]) == [exact]  # déjà exact
    assert client._resolve_measures("ds", ["part des recours avec offre d'emploi (switch %)"]) == [
        exact
    ]  # casse + ' droit
    assert client._resolve_measures("ds", ["Part des recours avec offre d'emploi"]) == [exact]  # par libellé
    assert client._resolve_measures("ds", ["inconnu"]) == ["inconnu"]  # laissé tel quel


def test_prep_substitutes_signatures_and_sid(mocker):
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    client.sigs = rpe.Signatures("PERM", "STRONG", "PLOG", "PDASH", "PASS")
    client.sid = "4c9184f37cff01abc"
    out = client._prep("__STRONG_NAME__|__POLICY_DASH__|4c9184f37cff01bcdc32")
    assert "STRONG" in out and "PDASH" in out and "4c9184f37cff01abc" in out and "__STRONG_NAME__" not in out


def test_no_baked_constants():
    assert not hasattr(rpe, "BAKED_PERMUTATION") and not hasattr(rpe, "BAKED_STRONG_NAME")


def test_refresh_persists_only_on_successful_validation(mocker):
    mocker.patch.object(rpe, "ensure_schema")
    client = mocker.MagicMock()
    client.refresh_catalog.return_value = ({"CK1": "CID"}, "<flows>")
    mocker.patch.object(rpe.RpeClient, "connect", return_value=client)
    mocker.patch.object(rpe, "build_toc", return_value=[{"cube_key": "CK1", "name": "DS"}])
    store_sig = mocker.patch.object(rpe, "store_signature")
    store_toc = mocker.patch.object(rpe, "store_toc", return_value=1)
    mocker.patch.object(rpe, "_canary_ok", return_value=True)
    rpe.refresh()
    store_sig.assert_called_once()
    store_toc.assert_called_once()


def test_refresh_alerts_and_skips_persist_on_canary_failure(mocker):
    mocker.patch.object(rpe, "ensure_schema")
    mocker.patch.object(rpe.RpeClient, "connect", return_value=mocker.MagicMock())
    mocker.patch.object(rpe, "_canary_ok", return_value=False)
    store_sig = mocker.patch.object(rpe, "store_signature")
    alert = mocker.patch.object(rpe, "notify_alert_channel")
    rpe.refresh()
    store_sig.assert_not_called()
    alert.assert_called()


def test_global_territory_codes_derives_once_lightest_and_fails_fast(mocker):
    client = mocker.MagicMock()
    client.measures.return_value = [{"id": "M"}]
    geo_rows = [
        {"name": "Light", "dimensions": [{"id": "C_TERRITOIRE_ID", "nbMembers": 50}]},
        {"name": "Heavy", "dimensions": [{"id": "C_TERRITOIRE_ID", "nbMembers": 5}]},  # trié en premier, mais timeout
    ]

    def fake_query(dataset, dims, measures=None, timeout=None):
        if dataset == "Heavy":
            raise httpx.ReadTimeout("boom")
        return [{"member_code": "11"}, {"member_code": "84"}]

    client.query.side_effect = fake_query
    out = rpe.global_territory_codes(client, geo_rows)

    assert out["Région"] == ["11", "84"]
    heavy_calls = [c for c in client.query.call_args_list if c.args[0] == "Heavy"]
    assert len(heavy_calls) == 1  # Région échoue → on n'insiste pas sur les autres paliers du cube lourd


def test_load_catalog_from_toc(mocker):
    mocker.patch.object(
        rpe,
        "load_toc_rows",
        return_value=[
            {
                "cube_key": "CK1",
                "cube_id": "CID",
                "name": "DS",
                "measures": [{"id": "M", "label": "M"}],
                "dimensions": [{"id": "C_TERRITOIRE_ID", "name": "Terr"}],
                "territory_codes": {"Département": ["78"]},
                "charts": [],
            }
        ],
    )
    cat, cubeids = rpe.catalog_from_toc()
    assert cubeids["CK1"] == "CID"
    assert cat["CK1"]["cubeName"] == "DS" and cat["CK1"]["measures"][0]["id"] == "M"


def test_relogin_rewires_session_and_persists(mocker):
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    client.sigs = rpe.Signatures("PERM", "STRONG", "PLOG", "PDASH", "PASS")
    client.bundle_nocache = None
    old_http = mocker.MagicMock()
    client.http = old_http
    new_http = mocker.MagicMock()
    new_http.cookies.get.return_value = "JSNEW"
    new_sigs = rpe.Signatures("PERM2", "STRONG2", "PLOG", "PDASH", "PASS")
    mocker.patch("lib.rpe.login", return_value=(new_http, new_sigs))
    mocker.patch.object(rpe.RpeClient, "_resolve_sid", return_value="SIDNEW")
    store = mocker.patch("lib.rpe.store_signature")
    client._relogin()
    old_http.close.assert_called_once()
    assert client.http is new_http
    assert (client.sigs.permutation, client.sigs.strong_name, client.sid) == ("PERM2", "STRONG2", "SIDNEW")
    store.assert_called_once_with(new_sigs, "SIDNEW", "JSNEW", None)


def test_gwt_relogins_when_not_ok_then_retries(mocker):
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    client.sid = "SID"
    client.sigs = rpe.Signatures("PERM", "STRONG", "PLOG", "PDASH", "PASS")
    rbad = mocker.MagicMock(status_code=403, text="forbidden")
    rok = mocker.MagicMock(status_code=200, text="//OK[data]")
    client.http = mocker.MagicMock()
    client.http.post.side_effect = [rbad, rok]
    relogin = mocker.patch.object(rpe.RpeClient, "_relogin")
    assert client._gwt("payload __STRONG_NAME__") == "//OK[data]"
    relogin.assert_called_once()
    assert client.http.post.call_count == 2


@pytest.mark.parametrize(
    "outcome,expected_ok",
    [("client", True), (None, False), ("raise", False)],
)
def test_check_connectivity(mocker, outcome, expected_ok):
    mocker.patch.object(rpe, "load_signatures", return_value=rpe.Signatures("P", "S", "L", "D", "PASS"))
    if outcome == "raise":
        mocker.patch.object(rpe, "_attempt_login", side_effect=httpx.ConnectError("boom"))
    else:
        mocker.patch.object(rpe, "_attempt_login", return_value=mocker.MagicMock() if outcome == "client" else None)
    ok, _ = rpe.check_connectivity(timeout=1)
    assert ok is expected_ok


def test_refresh_alerts_on_empty_toc(mocker):
    mocker.patch.object(rpe, "ensure_schema")
    client = mocker.MagicMock()
    client.refresh_catalog.return_value = ({"k": "cube"}, "<flows>")
    mocker.patch.object(rpe.RpeClient, "connect", return_value=client)
    mocker.patch.object(rpe, "_canary_ok", return_value=True)
    mocker.patch.object(rpe, "store_signature")
    mocker.patch.object(rpe, "build_toc", return_value=[])
    mocker.patch.object(rpe, "store_toc", return_value=0)
    alert = mocker.patch.object(rpe, "notify_alert_channel")
    out = rpe.refresh()
    assert out == {"ok": True, "datasets": 0}
    alert.assert_called_once()  # TOC vide → alerte cache inchangé


@pytest.mark.integration
def test_live_login_query():
    client = rpe.RpeClient.connect()
    try:
        _fresh, flows = client.refresh_catalog()  # catalogue dérivé en httpx (pas de JSON committé)
        toc = rpe.build_toc(client, flows)
        client.catalog = {r["cube_key"]: {"cubeName": r["name"], "dimensions": r["dimensions"]} for r in toc}
        names = {r["name"] for r in toc}
        assert DATASET in names  # le cube métier lourd est catalogué (sans requête : compute serveur trop coûteux)
        # Requête réelle sur un cube léger (les gros cubes peuvent recalculer >60s après rotation nocturne).
        light = next(n for n in ("Indicateurs", "NPS", "Satisfaction DE") if n in names)
        rows = client.query(light, [client.dimensions(light)[0]["id"]], timeout=90)
        assert all("member_code" in r for r in rows)  # parse correct (cube léger peut renvoyer 0 ligne)
    finally:
        client.close()


@pytest.mark.integration
def test_live_refresh_catalog_returns_cubeids():
    client = rpe.RpeClient.connect()
    try:
        fresh, _flows = client.refresh_catalog()
        assert len(fresh) >= 5
        assert all(rpe.CUBE_RE.fullmatch(v) for v in fresh.values())
    finally:
        client.close()


def test_build_toc_dims_from_cube_dm_measures_charts_excludes_ddaudit(mocker):
    mocker.patch.object(rpe, "cube_dm_urls", return_value={"CK1": "/url1", "CKaudit": "/url2"})
    mocker.patch.object(
        rpe,
        "parse_charts",
        return_value=[
            {"cube_key": "CK1", "measures_shown": ["Taux A", "Taux B"], "dims_shown": []},
            {"cube_key": "CK1", "measures_shown": ["Taux A"], "dims_shown": []},  # mesure déjà vue
            {"cube_key": "CKaudit", "measures_shown": ["Audit"], "dims_shown": []},
        ],
    )
    mocker.patch.object(
        rpe,
        "parse_cube_dm",
        side_effect=lambda js: {
            "/url1": {
                "cube_name": "Accès et présence en emploi",
                "dimensions": [
                    {
                        "id": "C_TERRITOIRE_ID",
                        "name": "Territoire",
                        "category": "1. Territoire",
                        "caption_dim": "C_LBLTERRITOIRE",
                        "n_members": 363,
                        "time": False,
                    }
                ],
            },
            "/url2": {"cube_name": "DDAudit: Sessions", "dimensions": []},
        }[js],
    )
    client = mocker.MagicMock()
    client.fetch_cube_dm.side_effect = lambda url, **kw: url
    rows = rpe.build_toc(client, "FLOWS")
    assert {r["cube_key"] for r in rows} == {"CK1"}  # DDAudit exclu
    row = rows[0]
    assert row["name"] == "Accès et présence en emploi"
    assert row["measures"] == [{"id": "Taux A", "label": "Taux A"}, {"id": "Taux B", "label": "Taux B"}]
    assert row["dimensions"][0] == {
        "id": "C_TERRITOIRE_ID",
        "name": "Territoire",
        "category": "1. Territoire",
        "captionDim": "C_LBLTERRITOIRE",
        "nbMembers": 363,
        "time": False,
    }
    assert len(row["charts"]) == 2  # graphes du cube portés dans la TOC


def test_build_toc_skips_unreachable_cube_dm(mocker):
    mocker.patch.object(rpe, "cube_dm_urls", return_value={"CK1": "/ok", "CK2": "/boom"})
    mocker.patch.object(rpe, "parse_charts", return_value=[])
    mocker.patch.object(rpe, "parse_cube_dm", return_value={"cube_name": "Cube 1", "dimensions": []})
    client = mocker.MagicMock()

    def fetch(url, **kw):
        if url == "/boom":
            raise httpx.ConnectError("down")
        return url

    client.fetch_cube_dm.side_effect = fetch
    rows = rpe.build_toc(client, "FLOWS")
    assert {r["cube_key"] for r in rows} == {"CK1"}  # le cube en échec est absent


def test_store_toc_full_replace_and_empty_guard():
    from sqlalchemy import text

    from web.db import get_engine

    rpe.ensure_schema()
    rows = [
        {
            "cube_key": "__ck1__",
            "cube_id": "cid1",
            "name": "__ds1__",
            "measures": [{"id": "M1", "label": "Mesure 1"}],
            "dimensions": [{"id": "D1"}],
            "territory_codes": {"Région": ["11"]},
            "charts": [],
        },
        {"cube_key": "__ck2__", "cube_id": "cid2", "name": "__ds2__"},
    ]
    assert rpe.store_toc(rows) == 2
    assert rpe.store_toc([{"cube_key": "__ck1__", "cube_id": "cid1", "name": "__ds1__"}]) == 1  # remplacement complet
    with get_engine().connect() as c:
        keys = {r[0] for r in c.execute(text("SELECT cube_key FROM dashboard_storage.rpe_toc"))}
    assert keys == {"__ck1__"}  # __ck2__ disparu
    assert rpe.store_toc([]) == 0  # TOC vide → pas d'écrasement
    with get_engine().connect() as c:
        assert c.execute(text("SELECT count(*) FROM dashboard_storage.rpe_toc")).scalar() == 1
    with get_engine().begin() as c:
        c.execute(text("DELETE FROM dashboard_storage.rpe_toc"))


def test_query_uses_shared_sel_and_blank_frame(mocker):
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    client.catalog = {"CK1": {"cubeName": DATASET, "dimensions": [], "measures": [{"id": "m1", "label": "M1"}]}}
    client.cubeids = {"CK1": "CUBE123"}
    captured = {}

    class FakeResp:
        def json(self):
            return {
                "axis": [[{"i": "m1", "f": "M1"}], [{"i": "84", "f": "ARA"}]],
                "lines": [[0, 0, 5.0]],
                "dimsAndMeasuresHeaders": ["Region"],
            }

    def fake_post(params, timeout=60):
        captured.update(params)
        return FakeResp()

    mocker.patch.object(client, "_post_file", side_effect=fake_post)
    rows = client.query(DATASET, ["C_TERRITOIRE_ID"], measures=["m1"])
    assert rows and rows[0]["value"] == 5.0
    sel = json.loads(captured["sel"])
    assert sel["measuresToKeep"] == ["m1"]
    assert captured["frameId"] == "" and captured["pageId"] == ""


@pytest.mark.integration
def test_live_toc_populated():
    from sqlalchemy import text

    from web.db import get_engine

    rpe.ensure_schema()
    client = rpe.RpeClient.connect()
    try:
        _fresh, flows = client.refresh_catalog()
        rows = rpe.build_toc(client, flows)
    finally:
        client.close()
    n = rpe.store_toc(rows)
    assert n >= 5  # FT ajoute/retire des datasets ; borne basse souple
    with get_engine().connect() as c:
        hits = c.execute(
            text(
                "SELECT count(*) FROM dashboard_storage.rpe_toc "
                "WHERE charts::text ILIKE '%recours%' OR measures::text ILIKE '%recours%'"
            )
        ).scalar()
    assert hits >= 1


def test_refresh_catalog_uses_all_wallet_frames(mocker):
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    client.cubeids = {}
    wallet = '//OK[["A","11aa11","B","22bb22"],7]'
    k1 = "fba0c2c4f5e0987f8c5d1cdd5bba387a"
    k2 = "41394d15cebee6301ae0d5c2bb76512d"
    flows = f'"{k1}_{"0" * 32}_0_1700000000000","{k2}_{"0" * 32}_0_1700000000000"'

    def fake_gwt(payload):
        if "loadWallet" in payload:
            return wallet
        if "ItemIdentifier" in payload:
            return flows
        return ""

    mocker.patch.object(client, "_gwt", side_effect=fake_gwt)
    fresh, flows = client.refresh_catalog()
    assert set(fresh) == {k1, k2}
    assert k1 in flows
