"""A UUID spelled in Crockford base32: 26 lowercase characters, read back whatever their case."""

import re
import uuid

__all__ = ["decode", "encode"]

ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"


def encode(value: str) -> str:
    """The UUID's 128 bits in Crockford base32, zero-padded to 26 characters."""
    number = uuid.UUID(value).int
    return "".join(ALPHABET[(number >> shift) & 31] for shift in range(125, -1, -5))


def decode(text: str) -> str | None:
    """The UUID a 26-character spelling stands for, None for any other text."""
    if not re.fullmatch(r"[0-9a-hjkmnp-tv-z]{26}", text, re.IGNORECASE):
        return None
    number = 0
    for char in text.lower():
        number = (number << 5) | ALPHABET.index(char)
    # Why: 26 characters hold 130 bits; a first character above 7 spells more than a UUID's 128.
    return str(uuid.UUID(int=number)) if number >> 128 == 0 else None
