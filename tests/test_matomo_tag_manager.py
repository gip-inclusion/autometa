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
            "matomo_url": "https://matomo.example.test",
        },
    )
    html = templates.get_template("base.html").render()

    if expected_present:
        head = html.split("</head>", 1)[0]
        assert "Matomo Tag Manager" in head
        assert "g.async = true" in head
        assert "https://matomo.example.test/js/container_abc123de.js" in head
        assert html.count("https://matomo.example.test/js/container_abc123de.js") == 1
    else:
        assert "Matomo Tag Manager" not in html
        assert "_mtm" not in html
        assert "container_" not in html
