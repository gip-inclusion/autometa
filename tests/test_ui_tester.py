import pytest

from skills.debug_matomo_ui.scripts.ui_tester import build_ui_url, discover_categories


@pytest.mark.parametrize(
    ("segment", "fragment"),
    [
        (None, "#?category=General_Visitors&subcategory=General_Overview"),
        ("dimension3==SIAE", "#?category=General_Visitors&subcategory=General_Overview&segment=dimension3%3D%3DSIAE"),
    ],
)
def test_build_ui_url_targets_configured_matomo(mocker, segment, fragment):
    mocker.patch("skills.debug_matomo_ui.scripts.ui_tester.get_matomo").return_value.url = "matomo.example.org"

    url = build_ui_url(117, "month", "2026-09-01", "General_Visitors", "General_Overview", segment)

    assert url == (
        "https://matomo.example.org/index.php?module=CoreHome&action=index&idSite=117&period=month&date=2026-09-01"
        + fragment
    )


def test_discover_categories_groups_subcategories(mocker):
    widgets = [
        {"category": {"id": "General_Visitors"}, "subcategory": {"id": "General_Overview", "name": "Overview"}},
        {"category": {"id": "General_Visitors"}, "subcategory": {"id": "General_Overview", "name": "Overview"}},
        {"category": {"id": "Goals_Goals"}, "subcategory": "Goals_Ecommerce"},
        {"category": {"id": "Goals_Goals"}, "subcategory": None},
    ]
    matomo = mocker.patch("skills.debug_matomo_ui.scripts.ui_tester.get_matomo").return_value
    matomo.request.return_value = widgets

    assert discover_categories(site_id=117) == {
        "General_Visitors": [("General_Overview", "Overview")],
        "Goals_Goals": [("Goals_Ecommerce", "")],
    }
    matomo.request.assert_called_once_with("API.getWidgetMetadata", timeout=30, idSite=117)
