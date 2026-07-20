import pytest

from lib.pii import NIR_PLACEHOLDER, is_valid_nir, redact_nir


# Structurally valid NIRs (INSEE key computed, not real people).
def _nir(body="185057800608"):
    body13 = (body + "0")[:13]
    return f"{body13}{97 - (int(body13) % 97):02d}"


@pytest.mark.parametrize(
    "digits, expected",
    [
        (_nir(), True),
        (_nir()[:14], False),
        (_nir() + "0", False),
        ("9" + _nir()[1:], False),
        ("0" + _nir()[1:], False),
        (_nir()[:13] + "00", False),
        ("12345678901234a", False),
        ("", False),
    ],
)
def test_is_valid_nir(digits, expected):
    assert is_valid_nir(digits) is expected


@pytest.mark.parametrize("template", ["numéro {} merci", "{}", "NIR:{}.", "n° {} et autre texte"])
def test_redact_nir_blanks_valid_numbers(template):
    out = redact_nir(template.format(_nir()))
    assert _nir() not in out
    assert NIR_PLACEHOLDER in out


@pytest.mark.parametrize("sep", [" ", ".", "-"])
def test_redact_nir_handles_separators(sep):
    n = _nir()
    spaced = sep.join([n[0], n[1:3], n[3:5], n[5:7], n[7:10], n[10:13], n[13:]])
    out = redact_nir(f"voici {spaced} fin")
    assert NIR_PLACEHOLDER in out
    assert not any(part in out for part in [n[7:10], n[10:13]])


@pytest.mark.parametrize(
    "text",
    [
        "appelez le 06 12 34 56 78",
        "commande 123456789012345",
        "SIRET 12345678901234",
        "",
        "aucun chiffre ici",
    ],
)
def test_redact_nir_leaves_non_nir_untouched(text):
    assert redact_nir(text) == text


def test_redact_nir_blanks_several_occurrences():
    a, b = _nir("185057800608"), _nir("269108712345")
    out = redact_nir(f"{a} et {b}")
    assert a not in out and b not in out
    assert out.count(NIR_PLACEHOLDER) == 2


def test_redact_nir_preserves_surrounding_text():
    out = redact_nir(f"avant {_nir()} après")
    assert out == f"avant {NIR_PLACEHOLDER} après"
