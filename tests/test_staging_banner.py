"""Tests for the staging warning banner in base.html."""

import pytest

from web.deps import templates
from web.environment import Environment


@pytest.mark.parametrize("is_staging", [True, False])
def test_staging_banner(mocker, is_staging):
    mocker.patch.dict(templates.env.globals, {"is_staging": is_staging})
    html = templates.get_template("base.html").render()
    assert ("Version de staging, ne pas utiliser" in html) is is_staging


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
