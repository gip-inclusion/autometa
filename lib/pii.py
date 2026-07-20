"""Détection et anonymisation de données personnelles dans du texte libre."""

import re

NIR_PLACEHOLDER = "[NIR-ANONYMISÉ]"
# NIR = 13-digit body + 2-digit INSEE key, often written with spaces/dots/dashes.
DIGIT_RUN = re.compile(r"[1-8][0-9 .\-]{12,22}[0-9]")

__all__ = ["NIR_PLACEHOLDER", "is_valid_nir", "redact_nir"]


def is_valid_nir(digits: str) -> bool:
    """True if 15 digits form a NIR whose INSEE check key matches."""
    if len(digits) != 15 or digits[0] not in "12345678":
        return False
    try:
        return int(digits[13:]) == 97 - (int(digits[:13]) % 97)
    except ValueError:
        return False


def redact_nir(text: str) -> str:
    """Blank every valid NIR in text. Key validation keeps phone/order numbers untouched."""
    if not text:
        return text
    for match in reversed(list(DIGIT_RUN.finditer(text))):
        raw = match.group(0)
        positions = [i for i, ch in enumerate(raw) if ch.isdigit()]
        digits = "".join(raw[i] for i in positions)
        for start in range(len(digits) - 14):
            if is_valid_nir(digits[start : start + 15]):
                lo = match.start() + positions[start]
                hi = match.start() + positions[start + 14] + 1
                text = text[:lo] + NIR_PLACEHOLDER + text[hi:]
                break
    return text
