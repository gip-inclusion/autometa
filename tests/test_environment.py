import pytest

from web.environment import Environment


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, Environment.DEV),
        ("", Environment.DEV),
        ("dev", Environment.DEV),
        ("review", Environment.REVIEW),
        ("staging", Environment.STAGING),
        ("prod", Environment.PROD),
    ],
)
def test_current_resolves_known_values(raw, expected):
    assert Environment.current(raw) is expected


@pytest.mark.parametrize("raw", ["live", "prd", "Production", "staign"])
def test_current_fails_loud_on_unknown_value(raw):
    with pytest.raises(ValueError):
        Environment.current(raw)


@pytest.mark.parametrize(
    ("env", "is_server"),
    [
        (Environment.DEV, False),
        (Environment.REVIEW, True),
        (Environment.STAGING, True),
        (Environment.PROD, True),
    ],
)
def test_is_server_is_true_off_local(env, is_server):
    assert env.is_server is is_server


@pytest.mark.parametrize(
    ("env", "owns"),
    [
        (Environment.DEV, False),
        (Environment.REVIEW, False),
        (Environment.STAGING, False),
        (Environment.PROD, True),
    ],
)
def test_only_prod_owns_the_shared_db(env, owns):
    assert env.owns_shared_db is owns


def test_member_is_its_string_value():
    assert Environment.PROD == "prod"
    assert Environment.PROD.value == "prod"
