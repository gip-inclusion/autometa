"""Replace PII (emails, phones) in JSONL/JSON files in-place. Safe-list well-known no-reply addresses."""

import argparse
import hashlib
import re
import sys
from pathlib import Path

SAFE_EMAILS = {"noreply@anthropic.com", "noreply@scalingo.com"}
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:0[1-9](?:[\s.-]?\d{2}){4}|\+33[\s.-]?\d(?:[\s.-]?\d{2}){4})(?!\d)")


def _hash_email(email: str) -> str:
    return f"<EMAIL_{hashlib.sha256(email.lower().encode()).hexdigest()[:8]}>"


def _replace_email(m: re.Match) -> str:
    addr = m.group(0)
    return addr if addr.lower() in SAFE_EMAILS else _hash_email(addr)


def pseudonymize_text(text: str) -> str:
    text = EMAIL_RE.sub(_replace_email, text)
    text = PHONE_RE.sub("<PHONE_REDACTED>", text)
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="Pseudonymize PII in JSONL/JSON files")
    parser.add_argument("directory", type=Path, help="Directory to process recursively")
    parser.add_argument("--ext", nargs="+", default=["jsonl", "json"], help="File extensions to process")
    args = parser.parse_args()

    total_emails = total_phones = 0
    for ext in args.ext:
        for path in args.directory.rglob(f"*.{ext}"):
            text = path.read_text(encoding="utf-8")
            emails = sum(1 for m in EMAIL_RE.finditer(text) if m.group(0).lower() not in SAFE_EMAILS)
            phones = len(PHONE_RE.findall(text))
            if emails or phones:
                path.write_text(pseudonymize_text(text), encoding="utf-8")
                total_emails += emails
                total_phones += phones
                print(f"{path}: {emails} emails, {phones} phones")

    print(f"Total: {total_emails} emails, {total_phones} phones", file=sys.stderr)


if __name__ == "__main__":
    main()
