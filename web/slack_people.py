"""Qui, dans Slack, est des nôtres : une personne membre à part entière de notre espace, un canal qui n'en sort pas."""

import logging
import time

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

people: dict[str, tuple[float, dict]] = {}
home: dict[str, str] = {}


def team(web: WebClient) -> str | None:
    """L'espace Slack où l'application est installée, lu une fois."""
    if not home.get("team"):
        home["team"] = web.auth_test().get("team_id")
    return home["team"]


def one_line(name: str | None) -> str:
    """Un nom que choisit une personne ou une application, sur une seule ligne : il ne peut pas en ouvrir une autre."""
    return " ".join((name or "").split())[:80]


def person(web: WebClient, user_id: str) -> dict:
    """Le nom d'un membre de Slack, son adresse, s'il est invité ou extérieur, et s'il est membre de notre espace."""
    known = people.get(user_id)
    # Why: un invité promu, un compte désactivé : ce que Slack a dit d'une personne ne vaut que dix minutes.
    if known and known[0] > time.monotonic():
        return known[1]
    if len(people) >= 2000:
        people.clear()
    user = web.users_info(user=user_id)["user"]
    profile = user.get("profile") or {}
    guest = any(user.get(flag) for flag in ("is_restricted", "is_ultra_restricted", "is_stranger"))
    # Why: sur Enterprise Grid, une personne a plusieurs espaces ; celui de l'application peut ne pas être le premier.
    teams = (user.get("team_id"), *(user.get("enterprise_user") or {}).get("teams", []))
    ours = bool(team(web)) and team(web) in teams
    people[user_id] = (
        time.monotonic() + 600,
        {
            "name": one_line(profile.get("display_name") or user.get("real_name") or profile.get("real_name"))
            or "Quelqu'un",
            "email": (profile.get("email") or "").lower(),
            "guest": guest,
            "member": ours and not (guest or user.get("is_bot") or user.get("deleted")),
        },
    )
    return people[user_id][1]


def outside(web: WebClient, channel: str) -> bool:
    """Vrai pour un canal partagé avec une autre organisation, autant que Slack le dise au bot."""
    try:
        info = web.conversations_info(channel=channel)["channel"]
    except SlackApiError as error:
        # Why: le bot ne lit que les canaux publics (channels:read) ; d'un canal privé, seule la personne est jugée.
        logger.info("Canal Slack %s illisible, partage inconnu : %s", channel, error.response.get("error"))
        return False
    return any(info.get(flag) for flag in ("is_ext_shared", "is_org_shared", "is_pending_ext_shared"))
