"""A UUID spelled in Crockford base32 and read back."""

import uuid

import pytest

from lib import crockford


def test_a_spelling_reads_back_as_its_uuid():
    for _ in range(200):
        value = str(uuid.uuid4())

        assert crockford.decode(crockford.encode(value)) == value


@pytest.mark.parametrize(
    ("value", "spelled"),
    [
        ("00000000-0000-0000-0000-000000000000", "0" * 26),
        ("00000000-0000-0000-0000-00000000001f", "0" * 25 + "z"),
        ("ffffffff-ffff-ffff-ffff-ffffffffffff", "7" + "z" * 25),
    ],
    ids=["zéro", "petit", "maximum"],
)
def test_a_spelling_is_26_lowercase_characters_padded_with_zeros(value, spelled):
    assert crockford.encode(value) == spelled
    assert crockford.decode(spelled) == value


def test_a_spelling_reads_back_whatever_its_case():
    value = str(uuid.uuid4())

    assert crockford.decode(crockford.encode(value).upper()) == value


@pytest.mark.parametrize(
    "text",
    ["0" * 25, "0" * 27, "0" * 25 + "u", "0" * 25 + "-", "8" + "0" * 25, "", "new", str(uuid.uuid4())],
    ids=["trop-court", "trop-long", "lettre-exclue", "tiret", "plus-de-128-bits", "vide", "mot", "uuid"],
)
def test_any_other_text_has_no_uuid(text):
    assert crockford.decode(text) is None
