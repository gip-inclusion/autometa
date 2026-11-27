"""Alerte quotidienne : tableaux de bord sans visite Matomo depuis 60 jours, à archiver."""

import re
from datetime import datetime, timedelta

from lib.query import CallerType, execute_matomo_query
from web import config
from web.alerts import notify_alert_channel
from web.database import store
from web.helpers import utcnow

WINDOW_DAYS = 60


def visited_slugs(rows: list[dict]) -> set[str]:
    """Slugs de TDB vus dans les pages Matomo d'une journée, vues internes et publiques confondues."""
    slugs = set()
    for row in rows:
        label = row["label"]
        if label in ("/interactive/ - Others", "/dashboards/ - Others"):
            raise RuntimeError(f"Matomo a regroupé des pages en « {label} » : visites incomplètes")
        parts = re.split(r"[?#]", label)[0].split("/")
        # Why: la fiche Autometa (/dashboards/<slug>/edit) est la page où l'alerte envoie archiver ;
        # la compter ferait sortir de la liste tout TDB dont quelqu'un a seulement ouvert le lien.
        if parts[1:2] == ["dashboards"] and parts[3:4] == ["edit"]:
            continue
        if len(parts) > 2 and parts[1] in ("interactive", "dashboards") and parts[2]:
            slugs.add(parts[2])
    return slugs


def owner_name(email: str) -> str:
    """« Prenom Nom » déduit d'une adresse prenom.nom@…, sinon l'adresse elle-même."""
    local = email.split("@")[0]
    if "." not in local:
        return email
    return " ".join(part.title() for part in local.split("."))


def unused_dashboards_from(dashboards: list[dict], visited: set[str], now: datetime) -> list[dict]:
    """TDB créés avant la fenêtre et absents des visites, triés par titre."""
    cutoff = now - timedelta(days=WINDOW_DAYS)
    unused = [d for d in dashboards if d["created_at"] <= cutoff and d["slug"] not in visited]
    return sorted(unused, key=lambda d: d["title"])


def format_alert(dashboards: list[dict]) -> str:
    lines = [
        f"{len(dashboards)} tableaux de bord sans visite depuis {WINDOW_DAYS} jours — à archiver ? "
        "Prévenir les propriétaires."
    ]
    lines += [
        f"• {d['title']} — {owner_name(d['first_author_email'])} — {config.BASE_URL}/dashboards/{d['slug']}"
        for d in dashboards
    ]
    return "\n".join(lines)


def report_unused_dashboards() -> None:
    """Poste la liste des TDB sans visite ; lève sans rien poster si Matomo ne répond pas en entier."""
    now = utcnow()
    days = [(now - timedelta(days=offset)).date() for offset in range(1, WINDOW_DAYS + 1)]
    # Why: Matomo ne regroupe la traîne en « … - Others » que dans ses archives semaine, mois et plage ;
    # les archives jour restent détaillées, d'où une requête par jour, toutes dans un seul appel groupé.
    # 224 : site Matomo d'Autometa, qui compte les vues internes et publiques des TDB.
    urls = {
        f"urls[{i}]": f"method=Actions.getPageUrls&idSite=224&period=day&date={day}&flat=1&filter_limit=-1"
        for i, day in enumerate(days)
    }
    result = execute_matomo_query("inclusion", CallerType.CRON, "API.getBulkRequest", urls, timeout=60)
    if not result.success:
        raise RuntimeError(f"Matomo indisponible : {result.error}")

    visited = set()
    for day, rows in zip(days, result.data, strict=True):
        if isinstance(rows, dict):
            raise RuntimeError(f"Matomo en erreur pour le {day} : {rows.get('message')}")
        visited |= visited_slugs(rows)

    unused = unused_dashboards_from(store.list_dashboards(), visited, now)
    if unused:
        notify_alert_channel(format_alert(unused))
