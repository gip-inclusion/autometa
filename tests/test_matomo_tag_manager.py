"""Tests for the Matomo Tag Manager snippet rendering in base.html."""

import pytest

from web.deps import templates


@pytest.mark.parametrize(
    "container_id,expected_present",
    [
        ("abc123de", True),
        ("", False),
    ],
)
def test_matomo_tag_manager_snippet(mocker, container_id, expected_present):
    mocker.patch.dict(
        templates.env.globals,
        {
            "matomo_tag_manager_container_id": container_id,
            "matomo_tracking_url": "https://matomo.example.test",
        },
    )
    html = templates.get_template("base.html").render()
    assert ("container_abc123de.js" in html) is expected_present
