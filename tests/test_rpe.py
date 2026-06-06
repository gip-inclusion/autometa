"""Tests for lib/rpe.py — sel building, response parsing, period resolution, and live RPE access."""

import json

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
