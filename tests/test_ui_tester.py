from skills.debug_matomo_ui.scripts.ui_tester import discover_categories


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
