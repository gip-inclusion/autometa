"""Tests for sync_sites and sync_metabase scripts."""

import pytest

from skills.sync_sites.scripts.sync_sites import (
    SITES,
    fetch_custom_dimensions,
    fetch_event_names,
    fetch_saved_segments,
)


def test_site_config_sites_defined():
    expected = {"emplois", "pilotage", "communaute", "dora", "plateforme", "rdv-insertion", "mon-recap", "marche"}
    assert set(SITES.keys()) == expected


def test_site_config_emplois_config():
    emplois = SITES["emplois"]
    assert emplois.matomo_id == 117
    assert emplois.user_kind_dimension == 1


def test_fetch_custom_dimensions(mocker):
    mock_api = mocker.MagicMock()
    mock_api.get_configured_dimensions.return_value = [
        {"idcustomdimension": 1, "name": "UserKind", "scope": "visit", "active": True},
        {"idcustomdimension": 2, "name": "Unused", "scope": "visit", "active": False},
    ]
    result = fetch_custom_dimensions(mock_api, 117)
    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["name"] == "UserKind"


def test_fetch_saved_segments(mocker):
    mock_api = mocker.MagicMock()
    mock_api._request.return_value = [
        {"name": "Candidats", "definition": "dimension1==job_seeker"},
    ]
    result = fetch_saved_segments(mock_api, 117)
    assert len(result) == 1
    assert result[0]["name"] == "Candidats"


def test_fetch_event_names(mocker):
    mock_api = mocker.MagicMock()
    mock_api.get_event_names.return_value = [
        {"label": "click_candidature", "nb_events": 490000, "nb_visits": 50000},
    ]
    result = fetch_event_names(mock_api, 117, "month", "2025-12-01")
    assert len(result) == 1
    assert result[0]["name"] == "click_candidature"
    assert result[0]["events"] == 490000


@pytest.mark.parametrize(
    "return_value",
    [
        "not a list",
        None,
    ],
)
def test_fetch_saved_segments_bad_response(mocker, return_value):
    mock_api = mocker.MagicMock()
    mock_api._request.return_value = return_value
    assert fetch_saved_segments(mock_api, 117) == []
