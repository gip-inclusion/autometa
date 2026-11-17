"""Tests for the staging warning banner in base.html."""

import pytest

from web.deps import templates
from web.environment import Environment


@pytest.mark.parametrize("shows_staging_banner", [True, False])
def test_staging_banner(mocker, shows_staging_banner):
    mocker.patch.dict(templates.env.globals, {"shows_staging_banner": shows_staging_banner})
    html = templates.get_template("base.html").render()
    assert ("Version de test, ne pas utiliser" in html) is shows_staging_banner


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        (Environment.DEV, False),
        (Environment.REVIEW, True),
        (Environment.STAGING, True),
        (Environment.PROD, False),
    ],
)
def test_shows_staging_banner(env, expected):
    assert env.shows_staging_banner is expected
