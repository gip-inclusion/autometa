"""Weekly Slack DMs asking active users for Tally feedback."""

import logging
import sys
from datetime import timedelta
from urllib.parse import quote

from sqlalchemy import select

from lib.slack import lookup_user, post_message
from web.helpers import utcnow

from . import config
from .db import get_db
from .models import Conversation

logger = logging.getLogger(__name__)

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
    cutoff = utcnow() - timedelta(days=7)
    with get_db() as session:
        rows = session.scalars(select(Conversation.user_id).where(Conversation.updated_at >= cutoff).distinct()).all()
    return sorted({e.strip() for e in rows if e and e.strip() not in EXCLUDED_EMAILS})


def main():
    token = config.SLACK_BOT_TOKEN
    if not token:
        logger.error("SLACK_BOT_TOKEN is not set")
        sys.exit(1)

    emails = get_active_emails()
    logger.info("Found %d active user(s) in the last 7 days", len(emails))

    sent = 0
    for email in emails:
        slack_id = lookup_user(token, email)
        if not slack_id:
            logger.info("SKIP %s (no Slack user found)", email)
            continue
        tally_url = f"{TALLY_FORM_URL}?email={quote(email)}"
        ok = post_message(token, slack_id, SLACK_MESSAGE.format(tally_url=tally_url))
        logger.info("%s %s", "SENT" if ok else "FAIL", email)
        if ok:
            sent += 1

    logger.info("Done: %d sent", sent)
