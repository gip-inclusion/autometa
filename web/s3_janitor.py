"""Balayeur du bucket : snapshots de publications retirées, fichiers déposés orphelins, temporaires oubliés."""

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError
from sqlalchemy import or_, select

from web import alerts, config, s3
from web.backup_check import check_mirror_manifest
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
    unsaved = delete and not backed_up()
    delete = delete and not unsaved
    # Why: un passage coupé en route (délai, redémarrage) laisse ainsi la trace de ce qu'il allait effacer.
    trace = "\n".join(listing(garbage))
    logger.info("s3-janitor %s:\n%s", "sweeping" if delete else "dry run", trace)
    swept = [(store, e) for store, e in garbage if not delete or store.delete(e["path"])]
    report(swept, len(garbage) - len(swept), deleted=delete, unsaved=unsaved)


def backed_up() -> bool:
    """La sauvegarde du jour existe et se déclare complète : sans elle, un objet effacé ne se récupère pas."""
    try:
        check_mirror_manifest()
    except RuntimeError, ClientError:
        logger.warning("s3-janitor: no complete backup today, dry run instead", exc_info=True)
        return False
    return True


def listing(objects: list[tuple[s3.S3Store, dict]]) -> list[str]:
    """Une ligne par snapshot de publication et par conversation, le chemin seul pour un temporaire."""
    folders = Counter(store.key(folder(store, e["path"])) for store, e in objects)
    return [
        f"{key} ({n} fichier{'s' if n > 1 else ''})" if key.endswith("/") else key for key, n in sorted(folders.items())
    ]


def folder(store: s3.S3Store, path: str) -> str:
    """Le dossier sous lequel l'objet est compté."""
    if store is s3.publications:
        return "/".join(path.split("/")[:2]) + "/"
    if store is s3.uploads:
        # Why: le nom d'un fichier déposé reprend celui de l'usager (CV_Prénom_Nom.pdf) ; sa conversation suffit.
        return path.rpartition("/")[0] + "/"
    return path


def report(swept: list[tuple[s3.S3Store, dict]], failures: int, *, deleted: bool, unsaved: bool) -> None:
    """Le compte dans le canal d'alertes, la liste en fil, un snapshot ou une conversation par ligne."""
    count = len(swept)
    size = f"{sum(e['size'] for _, e in swept) / 1e6:.1f} Mo".replace(".", ",")
    files = f"{count} fichier{'s' if count > 1 else ''} ({size})"
    why = " faute de sauvegarde complète aujourd'hui" if unsaved else ""
    summary = (
        f":broom: Balayeur a effacé {files}"
        if deleted
        else f":broom: Balayeur aurait effacé {files} — dry run{why}, rien n'a été supprimé"
    )
    if failures:
        summary += f" ; S3 a refusé {failures} suppression{'s' if failures > 1 else ''}, voir les logs"
    logger.info("%s", summary)
    thread = alerts.notify_alert_channel(summary)
    if thread:
        for block in alerts.blocks(listing(swept)):
            alerts.notify_alert_channel(f"```\n{block}\n```", thread_ts=thread)
