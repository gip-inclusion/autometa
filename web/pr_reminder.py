"""Rappel quotidien, dans le canal d'alertes Slack, des pull requests ouvertes d'Autometa."""

import logging
from datetime import date

from lib import github
from web.alerts import notify_alert_channel

logger = logging.getLogger(__name__)


def line(pr: dict, today: date) -> str:
    title = pr["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    age = (today - date.fromisoformat(pr["created_at"][:10])).days
    return f"• <{pr['url']}|#{pr['number']} {title}> · @{pr['author']} · ouverte il y a {age} j"


def message(pulls: list[dict], today: date) -> str | None:
    """Le rappel : PR liées au backlog d'abord, puis les autres, les plus anciennes en premier."""
    if not pulls:
        return None
    ordered = sorted(pulls, key=lambda pr: ("backlog" not in pr["labels"], pr["created_at"]))
    title = ":eyes: 1 PR ouverte" if len(pulls) == 1 else f":eyes: {len(pulls)} PR ouvertes, à traiter dans cet ordre"
    return "\n".join([title, *(line(pr, today) for pr in ordered)])


def remind(today: date) -> None:
    """Poste le rappel du lundi au vendredi, sans les brouillons ; rien s'il n'y a aucune PR ouverte."""
    if today.weekday() >= 5:
        logger.info("rappel des PR non posté : week-end")
        return
    text = message([pr for pr in github.pulls("gip-inclusion/autometa", max_results=100) if not pr["draft"]], today)
    if not text:
        logger.info("rappel des PR non posté : aucune PR ouverte")
        return
    notify_alert_channel(text)
