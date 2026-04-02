"""Weekly Slack DMs asking active users for Tally feedback."""

import sys
from datetime import datetime, timedelta
from urllib.parse import quote

from sqlalchemy import select

from lib.slack import lookup_user, send_dm

from . import config
from .db import get_db
from .models import Conversation

TALLY_FORM_URL = "https://tally.so/r/9qdZvp"
EXCLUDED_EMAILS = {"admin@localhost", ""}

SLACK_MESSAGE = (
    ":wave: Bonjour !\n\n"
    "Vous avez utilisé *Autometa* cette semaine — merci !\n"
    "Pourriez-vous prendre 2 minutes pour nous faire un retour ?\n\n"
    ":point_right: <{tally_url}|Donner mon feedback>\n\n"
    "Vos retours nous aident à améliorer l'outil. Merci :pray:"
)


def get_active_emails() -> list[str]:
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    with get_db() as session:
        rows = session.scalars(select(Conversation.user_id).where(Conversation.updated_at >= cutoff).distinct()).all()
    return sorted({e.strip() for e in rows if e and e.strip() not in EXCLUDED_EMAILS})


def main():
    token = config.SLACK_BOT_TOKEN
    if not token:
        print("ERROR: SLACK_BOT_TOKEN is not set", file=sys.stderr)
        sys.exit(1)

    emails = get_active_emails()
    print(f"Found {len(emails)} active user(s) in the last 7 days")

    sent = 0
    for email in emails:
        slack_id = lookup_user(token, email)
        if not slack_id:
            print(f"  SKIP {email} (no Slack user found)")
            continue
        tally_url = f"{TALLY_FORM_URL}?email={quote(email)}"
        ok = send_dm(token, slack_id, SLACK_MESSAGE.format(tally_url=tally_url))
        print(f"  {'SENT' if ok else 'FAIL'} {email}")
        if ok:
            sent += 1

    print(f"\nDone: {sent} sent")
