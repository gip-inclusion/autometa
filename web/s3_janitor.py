"""Balayeur du bucket : snapshots de publications retirées, fichiers déposés orphelins, temporaires oubliés."""

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from web import alerts, config, s3
from web.db import get_db
from web.models import DashboardPublication, UploadedFile
from web.sync_to_s3 import UNSYNCED

logger = logging.getLogger(__name__)

# Why: une publication copie son snapshot avant d'écrire sa ligne, un fichier déposé part sur S3 avant la sienne ;
# un mois laisse aussi le temps de lire les comptes rendus du balayeur avant qu'un oubli ne coûte un fichier.
GRACE = timedelta(days=30)


def referenced(now: datetime) -> tuple[set[str], set[str]]:
    """Publications en ligne ou retirées depuis moins d'un mois, et fichiers déposés encore rattachés à une conversation."""
    with get_db() as session:
        publications = set(
            session.scalars(
                select(DashboardPublication.publication_id).where(
                    or_(
                        DashboardPublication.unpublished_at.is_(None), DashboardPublication.unpublished_at > now - GRACE
                    )
                )
            )
        )
        uploads = set(session.scalars(select(UploadedFile.stored_filename)))
    return publications, uploads


def find_garbage(publications: set[str], uploads: set[str], now: datetime) -> list[tuple[s3.S3Store, dict]]:
    """Objets que plus rien ne référence et que rien n'a modifiés depuis un mois."""
    candidates = [
        (s3.interactive, e) for e in s3.interactive.list_files(raise_errors=True) if UNSYNCED.search(e["path"])
    ]
    # Why: une base vide ou mal branchée ferait de tout un préfixe un orphelin ; sans référence, on n'y touche pas.
    if publications:
        candidates += [
            (s3.publications, e)
            for e in s3.publications.list_files(raise_errors=True)
            if e["path"].count("/") >= 2 and e["path"].split("/")[1] not in publications
        ]
    if uploads:
        candidates += [(s3.uploads, e) for e in s3.uploads.list_files(raise_errors=True) if e["path"] not in uploads]
    return [(store, e) for store, e in candidates if e["last_modified"] < now - GRACE]


def run(*, delete: bool) -> None:
    """Efface ce que plus rien ne référence depuis un mois, ou le liste seulement, et en rend compte sur Slack."""
    if not config.ENV.owns_bucket:
        logger.info("s3-janitor skipped: the %s bucket holds files its database does not know", config.ENV)
        return
    now = datetime.now(timezone.utc)
    garbage = find_garbage(*referenced(now), now)
    swept = [(store, e) for store, e in garbage if not delete or store.delete(e["path"])]
    report(swept, len(garbage) - len(swept), deleted=delete)


def report(swept: list[tuple[s3.S3Store, dict]], failures: int, *, deleted: bool) -> None:
    """Le compte dans le canal d'alertes, la liste en fil ; un snapshot de publication y tient sur une ligne."""
    count = len(swept)
    size = f"{sum(e['size'] for _, e in swept) / 1e6:.1f} Mo".replace(".", ",")
    files = f"{count} fichier{'s' if count > 1 else ''} ({size})"
    summary = (
        f":broom: Balayeur a effacé {files}"
        if deleted
        else f":broom: Balayeur aurait effacé {files} — dry run, rien n'a été supprimé"
    )
    if failures:
        summary += f" ; S3 a refusé {failures} suppression{'s' if failures > 1 else ''}, voir les logs"
    keys = Counter(
        store.key("/".join(e["path"].split("/")[:2]) + "/") if store is s3.publications else store.key(e["path"])
        for store, e in swept
    )
    lines = [f"{key} ({n} fichiers)" if n > 1 else key for key, n in sorted(keys.items())]
    logger.info("%s\n%s", summary, "\n".join(lines))
    thread = alerts.notify_alert_channel(summary)
    if thread:
        for block in blocks(lines):
            alerts.notify_alert_channel(f"```\n{block}\n```", thread_ts=thread)


def blocks(lines: list[str]) -> list[str]:
    """Les lignes regroupées en messages de moins de 3 000 caractères, sous la limite d'affichage de Slack."""
    grouped = [""]
    for line in lines:
        if grouped[-1] and len(grouped[-1]) + len(line) >= 3000:
            grouped.append("")
        grouped[-1] += f"{line}\n"
    return [block.rstrip("\n") for block in grouped if block]
