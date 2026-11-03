"""Tests for the staging warning banner in base.html."""

import pytest

from web.deps import templates


@pytest.mark.parametrize("is_staging", [True, False])
def test_staging_banner(mocker, is_staging):
    mocker.patch.dict(templates.env.globals, {"is_staging": is_staging})
    html = templates.get_template("base.html").render()
    assert ("Version de staging, ne pas utiliser" in html) is is_staging
