import pytest

import lib.rpe_build as rb


def make_current():
    return {
        "gwt": {"x": "y"},
        "sel": {"measuresToKeep": []},
        "datasets": {"k1": {"cubeName": "DS1"}, "k2": {"cubeName": "DS2"}},
        "catalog": {
            "k1": {"cubeName": "DS1", "dimensions": [{"id": "C_TERRITOIRE_ID"}], "measures": [{"id": "m1"}]},
            "k2": {"cubeName": "DS2", "dimensions": [{"id": "D"}], "measures": [{"id": "m2"}]},
        },
    }


def test_assemble_candidate_uses_fresh_cubeids_and_carries_catalog():
    current = make_current()
    fresh = {"k1": "k1_c_0_1", "k2": "k2_c_0_1"}
    cand = rb.assemble(current, fresh)
    assert cand["datasets"]["k1"]["cubeId"] == "k1_c_0_1"
    assert cand["catalog"] == current["catalog"]
    assert cand["sel"] == current["sel"]


def test_assemble_carries_cubeid_when_fresh_missing():
    cand = rb.assemble(make_current(), {"k1": "k1_c_0_1"})
    assert cand["datasets"]["k2"].get("cubeId") is None


@pytest.mark.parametrize(
    "fresh, smoke, expected_passed, expected_no_cubeid",
    [
        ({"k1": "k1_c_0_1"}, {"k1": 3, "k2": 0}, False, ["k2"]),
        ({"k1": "k1_c_0_1", "k2": "k2_c_0_1"}, {"k1": 3, "k2": 5}, True, []),
    ],
)
def test_validate_gate(fresh, smoke, expected_passed, expected_no_cubeid):
    cand = rb.assemble(make_current(), fresh)
    report = rb.gate(cand, smoke=smoke)
    assert report["passed"] is expected_passed
    assert report["failures"]["no_cubeid"] == expected_no_cubeid
    if expected_passed:
        assert report["coverage"]["cubeids"] == "2/2"
