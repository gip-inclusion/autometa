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
