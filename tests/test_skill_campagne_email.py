import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
PUBLIC_TEXTS = [
    ROOT / "skills" / "campagne_email" / "SKILL.md",
    ROOT / "knowledge" / "growth" / "ecrire-aux-professionnels.md",
]


@pytest.mark.parametrize("path", PUBLIC_TEXTS, ids=lambda p: p.name)
def test_public_texts_carry_no_personal_data(path):
    text = path.read_text(encoding="utf-8")
    assert set(re.findall(r"Bonjour ([A-ZÉ][a-zé]+)", text)) <= {"Madame", "Prénom"}
    assert set(re.findall(r"^\[?([A-ZÉ][a-zé]+)\]? de La plateforme", text, re.M)) <= {"Prénom"}
    assert re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", text) == []
    assert re.findall(r"(?:\+33\s?|\b0)[1-9](?:[\s.-]?\d{2}){4}\b", text) == []
