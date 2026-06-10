"""Tests for lib/rpe.py — sel building, response parsing, period resolution, and live RPE access."""

import json

import httpx
import pytest

from lib import rpe

DATASET = "Accès et présence en emploi"


def make_body(dim_axes, lines, headers, measures):
    return {
        "dimsAndMeasuresHeaders": headers,
        "axis": [measures, *dim_axes],
        "lines": lines,
    }


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
    assert rpe._period_of(sel, breakdown, member) == expected


def test_epoch_month():
    assert rpe._epoch_month(1756677600 + 43200) == "2025-09"


def test_query_builds_multidim_sel_and_parses(mocker):
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    client.sid = "sid"
    key = next(iter(rpe._RES["datasets"]))
    name = rpe._RES["datasets"][key]["cubeName"]
    client.cubeids = {key: "CUBEID"}

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
    client.cubeids = {}
    client.http = mocker.MagicMock()
    with pytest.raises(rpe.RpeLoginError):
        client.query(DATASET, ["C_LBLSEXE"], ["MID"])


def test_connect_reuses_cached_session(mocker):
    mocker.patch("lib.rpe.load_cached_session", return_value=("JS123", "SID456"))
    login_spy = mocker.patch("lib.rpe.login", side_effect=AssertionError("ne doit pas se reconnecter"))
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
    assert mod._grep(measures, "entrant") == [measures[0]]
    assert mod._grep(measures, None) == measures

    assert mod.parse_ddvar("0") == 0 and mod.parse_ddvar("-3") == -3  # numérique → int
    assert mod.parse_ddvar("Mensuel") == "Mensuel"  # non numérique → chaîne brute (pas de crash)


def test_mirror_plan_geo_labels_and_time():
    dims = [{"id": "C_TERRITOIRE_ID"}, {"id": "D_DATETAETPED", "time": True}, {"id": "C_LBLSEXE"}]
    plan = rpe._mirror_plan(dims)
    geo = {(label, spec.get("lPos")) for label, spec in plan if label}
    for level in rpe.MIRROR_GEO:  # géo nommée canonique, au bon niveau de C_TERRITOIRE_ID
        assert (level, rpe.GEO_LEVELS[level]["lPos"]) in geo
    assert any(label is None and spec["dim"] == "D_DATETAETPED" for label, spec in plan)  # temps (header brut)


def test_store_facts_full_replace():
    from sqlalchemy import text

    from web.db import get_engine

    rpe.ensure_schema()
    base = {
        "measure": "m",
        "measure_id": "m",
        "period": "2025-09",
        "dimension": "Région",
        "member_code": "11",
        "member_label": "IDF",
    }
    rpe.store_facts([{**base, "dataset": "__t1__", "value": 1.0}, {**base, "dataset": "__t2__", "value": 9.0}])
    rpe.store_facts([{**base, "dataset": "__t1__", "value": 2.0}])  # remplacement complet → __t2__ disparaît
    with get_engine().connect() as c:
        ds = [r[0] for r in c.execute(text("SELECT DISTINCT dataset FROM matometa.rpe_fact"))]
        v = c.execute(text("SELECT value FROM matometa.rpe_fact WHERE dataset='__t1__'")).scalar()
    assert ds == ["__t1__"] and v == 2.0
    assert rpe.store_facts([]) == 0  # payload vide → cache non vidé
    with get_engine().connect() as c:
        assert c.execute(text("SELECT count(*) FROM matometa.rpe_fact")).scalar() == 1
    with get_engine().begin() as c:
        c.execute(text("DELETE FROM matometa.rpe_fact WHERE dataset='__t1__'"))


def test_update_measure_labels_upsert():
    from sqlalchemy import text

    from web.db import get_engine

    rpe.ensure_schema()
    with get_engine().begin() as c:
        c.execute(text("DELETE FROM matometa.rpe_measure WHERE dataset='__t__'"))
        c.execute(rpe.rpe_measure.insert().values(dataset="__t__", measure_id="mid1", label="old"))
    rpe.update_measure_labels([
        {"dataset": "__t__", "measure_id": "mid1", "measure": "new"},
        {"dataset": "__t__", "measure_id": "mid2", "measure": "fresh"},
    ])
    with get_engine().connect() as c:
        got = dict(c.execute(text("SELECT measure_id, label FROM matometa.rpe_measure WHERE dataset='__t__'")).all())
    with get_engine().begin() as c:
        c.execute(text("DELETE FROM matometa.rpe_measure WHERE dataset='__t__'"))
    assert got == {"mid1": "new", "mid2": "fresh"}


def test_refresh_alerts_and_reraises_on_login_failure(mocker):
    mocker.patch.object(rpe, "ensure_schema")
    mocker.patch.object(rpe.RpeClient, "connect", side_effect=rpe.RpeLoginError("boom"))
    alert = mocker.patch.object(rpe, "notify_alert_channel")
    with pytest.raises(rpe.RpeLoginError):
        rpe.refresh()
    alert.assert_called_once()


def test_norm_unifies_apostrophes_case_space():
    assert rpe._norm("Part  des  RECOURS ’X") == "part des recours 'x"


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


def test_prep_substitutes_strong_name_and_sid():
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    client.strong_name = "NEWSTRONG"
    client.sid = "NEWSID"
    payload = f"{rpe.BAKED_STRONG_NAME}|4c9184f37cff01deadbeef|x"
    assert client._prep(payload) == "NEWSTRONG|NEWSID|x"


def test_relogin_rewires_session_and_saves(mocker):
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    old_http = mocker.MagicMock()
    client.http = old_http
    new_http = mocker.MagicMock()
    new_http.cookies.get.return_value = "JSNEW"
    mocker.patch("lib.rpe.login", return_value=(new_http, "PERM2", "STRONG2"))
    mocker.patch.object(rpe.RpeClient, "_resolve_sid", return_value="SIDNEW")
    save = mocker.patch("lib.rpe.save_session")
    client._relogin()
    old_http.close.assert_called_once()
    assert client.http is new_http
    assert (client.permutation, client.strong_name, client.sid) == ("PERM2", "STRONG2", "SIDNEW")
    save.assert_called_once_with("JSNEW", "SIDNEW")


def test_gwt_relogins_when_not_ok_then_retries(mocker):
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    client.sid = "SID"
    client.permutation = rpe.BAKED_PERMUTATION
    client.strong_name = rpe.BAKED_STRONG_NAME
    rbad = mocker.MagicMock(status_code=403, text="forbidden")
    rok = mocker.MagicMock(status_code=200, text="//OK[data]")
    client.http = mocker.MagicMock()
    client.http.post.side_effect = [rbad, rok]
    relogin = mocker.patch.object(rpe.RpeClient, "_relogin")
    assert client._gwt("payload " + rpe.BAKED_STRONG_NAME) == "//OK[data]"
    relogin.assert_called_once()
    assert client.http.post.call_count == 2


def test_mirror_records_failures_and_overrides_geo_label(mocker):
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    key = next(iter(rpe._RES["datasets"]))
    name = rpe._RES["datasets"][key]["cubeName"]
    client.cubeids = {key: "CUBEID"}
    mocker.patch.object(rpe.RpeClient, "dimensions", return_value=[{"id": "C_TERRITOIRE_ID"}])

    def fake_query(ds, dims, timeout=None):
        if dims[0] is rpe.GEO_LEVELS["Département"]:
            raise KeyError("boom")
        return [{"member_code": "84", "dimension": "ServerHeader"}]

    mocker.patch.object(rpe.RpeClient, "query", side_effect=fake_query)
    rows, failed = client.mirror()
    assert sorted({r["dimension"] for r in rows}) == ["CLPE", "Région"]  # libellé géo canonique imposé
    assert failed == [f"{name} / Département"]


@pytest.mark.parametrize("facts,failed,alerts", [(42, [], 0), (0, ["ds / Région"], 1)])
def test_refresh_success_and_alerts_on_empty_mirror(mocker, facts, failed, alerts):
    mocker.patch.object(rpe, "ensure_schema")
    client = mocker.MagicMock()
    client.refresh_catalog.return_value = ({"k": "cube"}, "")
    client.mirror.return_value = ([{"x": 1}] if facts else [], failed)
    mocker.patch.object(rpe.RpeClient, "connect", return_value=client)
    mocker.patch.object(rpe, "store_catalog")
    mocker.patch.object(rpe, "update_measure_labels", return_value=0)
    mocker.patch.object(rpe, "store_facts", return_value=facts)
    mocker.patch.object(rpe, "store_charts", return_value=0)
    alert = mocker.patch.object(rpe, "notify_alert_channel")
    out = rpe.refresh()
    assert out == {"cubeids": 1, "labels": 0, "facts": facts, "charts": 0, "failed": len(failed)}
    client.close.assert_called_once()
    assert alert.call_count == alerts


@pytest.mark.parametrize(
    "outcome,expected_ok",
    [("client", True), (None, False), ("raise", False)],
)
def test_check_connectivity(mocker, outcome, expected_ok):
    if outcome == "raise":
        mocker.patch.object(rpe, "_attempt_login", side_effect=httpx.ConnectError("boom"))
    else:
        mocker.patch.object(rpe, "_attempt_login", return_value=mocker.MagicMock() if outcome == "client" else None)
    ok, _ = rpe.check_connectivity(timeout=1)
    assert ok is expected_ok


@pytest.mark.integration
def test_live_login_query():
    client = rpe.RpeClient.connect()
    try:
        rows = client.query(DATASET, [{"dim": "C_TERRITOIRE_ID", "hPos": 0, "lPos": 1}])
        assert rows and all("member_code" in r for r in rows)
    finally:
        client.close()


@pytest.mark.integration
def test_live_refresh_catalog_returns_cubeids():
    client = rpe.RpeClient.connect()
    try:
        fresh = client.refresh_catalog()
        assert len(fresh) >= 5
        assert all(rpe._CUBE_RE.fullmatch(v) for v in fresh.values())
    finally:
        client.close()


def test_store_charts_full_replace():
    from sqlalchemy import text

    from web.db import get_engine

    rpe.ensure_schema()
    donor = next(iter(rpe._RES["catalog"]))  # any real cube_key from the loaded catalog
    rpe.store_charts([
        {"chart_title": "__c1__", "cube_key": donor, "measures_shown": ["m"], "dims_shown": ["d"]},
        {"chart_title": "__c2__", "cube_key": "zzz", "measures_shown": [], "dims_shown": []},
    ])
    rpe.store_charts([{"chart_title": "__c1__", "cube_key": donor, "measures_shown": ["m2"], "dims_shown": []}])
    with get_engine().connect() as c:
        titles = [r[0] for r in c.execute(text("SELECT chart_title FROM matometa.rpe_chart"))]
        row = c.execute(
            text("SELECT cube_name, measures_shown FROM matometa.rpe_chart WHERE chart_title='__c1__'")
        ).first()
    assert titles == ["__c1__"]  # full replace dropped __c2__
    assert row[0] is not None  # cube_name resolved from the catalog
    assert row[1] == ["m2"]
    assert rpe.store_charts([]) == 0  # empty parse → no wipe
    with get_engine().connect() as c:
        assert c.execute(text("SELECT count(*) FROM matometa.rpe_chart")).scalar() == 1
    with get_engine().begin() as c:
        c.execute(text("DELETE FROM matometa.rpe_chart"))


def test_query_uses_shared_sel_and_blank_frame(mocker):
    client = rpe.RpeClient.__new__(rpe.RpeClient)
    key = next(iter(rpe._RES["datasets"]))
    client.cubeids = {key: "CUBE123"}
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
    rows = client.query(rpe._RES["datasets"][key]["cubeName"], ["C_TERRITOIRE_ID"], measures=["m1"])
    assert rows and rows[0]["value"] == 5.0
    sel = json.loads(captured["sel"])
    assert sel["measuresToKeep"] == ["m1"]
    assert captured["frameId"] == "" and captured["pageId"] == ""


@pytest.mark.integration
def test_live_charts_populated():
    from sqlalchemy import text

    from lib.rpe_gwt import parse_charts
    from web.db import get_engine

    rpe.ensure_schema()
    client = rpe.RpeClient.connect()
    try:
        _fresh, flows = client.refresh_catalog()
    finally:
        client.close()
    n = rpe.store_charts(parse_charts(flows))
    assert n > 100  # FT adds/removes charts; loose lower bound, don't pin ~400
    with get_engine().connect() as c:
        hits = c.execute(
            text(
                "SELECT count(*) FROM matometa.rpe_chart "
                "WHERE chart_title ILIKE '%recours%' OR array_to_string(measures_shown, ' ') ILIKE '%recours%'"
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
    mocker.patch.dict(
        rpe._RES["gwt"],
        {
            "getUserParams": "getUserParams",
            "loadWallet": "loadWallet",
            "getFlowsView": ["7|3|19|" + "|".join(str(i) for i in range(1, 20)) + "|x|"],
        },
    )
    fresh, flows = client.refresh_catalog()
    assert set(fresh) == {k1, k2}
    assert k1 in flows
