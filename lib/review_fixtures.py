"""Jeu de démonstration des review apps : conversations et tableaux de bord typiques, sans donnée réelle."""

import argparse
import json
import logging
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import sentry_sdk
from sqlalchemy import delete, insert, select, update

from lib import query
from lib.dashboards import adopt_dashboard
from web import config, publications, s3
from web.db import get_db
from web.models import (
    Conversation,
    ConversationTag,
    CronRun,
    Dashboard,
    DashboardPublication,
    Message,
    PinnedItem,
    Report,
    Tag,
    UserFavorite,
)
from web.sentry import init_sentry

logger = logging.getLogger(__name__)

FIXTURES_DIR = config.BASE_DIR / "fixtures" / "review"


def load() -> dict:
    return json.loads((FIXTURES_DIR / "fixtures.json").read_text())


def seed() -> None:
    """Purge puis recrée le jeu : chaque déploiement le ramène à son état d'origine."""
    purge()
    data = load()
    with get_db() as session:
        known = set(session.scalars(select(Tag.name)))
        session.add_all(Tag(**tag) for tag in data["tags"] if tag["name"] not in known)
        session.flush()
        for spec in data["conversations"]:
            seed_conversation(session, spec)
    for spec in data["dashboards"]:
        seed_dashboard(spec)
    logger.info(
        "Jeu de démonstration en place : %d conversations, %d tableaux de bord",
        len(data["conversations"]),
        len(data["dashboards"]),
    )


def seed_conversation(session, spec: dict) -> None:
    user = spec["owner"]
    created = datetime.now(timezone.utc) - timedelta(days=spec["days_ago"])
    rows = []
    if "forked_from" in spec:
        source = select(Message.type, Message.content, Message.timestamp).where(
            Message.conversation_id == spec["forked_from"]
        )
        rows = list(session.execute(source.order_by(Message.id)))
    repeat = spec.get("repeat")
    turns = [(kind, body, n) for n in range(1, (repeat or 1) + 1) for kind, body in spec["messages"]]
    flag_reason = spec.get("flag_reason")
    session.add(
        Conversation(
            id=spec["id"],
            user_id=user,
            title=spec["title"],
            forked_from=spec.get("forked_from"),
            flagged_at=created if flag_reason else None,
            flag_reason=flag_reason,
            flag_user_id=user if flag_reason else None,
            created_at=created,
            updated_at=created + timedelta(seconds=20 * len(turns)),
        )
    )
    session.flush()
    tag_ids = session.scalars(select(Tag.id).where(Tag.name.in_(spec["tags"])))
    session.add_all(ConversationTag(conversation_id=spec["id"], tag_id=tag_id) for tag_id in tag_ids)

    for i, (kind, body, n) in enumerate(turns):
        if kind == "report":
            report = Report(
                **body, source_conversation_id=spec["id"], user_id=user, created_at=created, updated_at=created
            )
            session.add(report)
            session.flush()
            body = {"report_id": report.id, "title": report.title}
        content = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
        rows.append((kind, content.replace("{n}", str(n)) if repeat else content, created + timedelta(seconds=20 * i)))
    session.execute(
        insert(Message),
        [
            {"conversation_id": spec["id"], "type": kind, "role": kind, "content": content, "timestamp": timestamp}
            for kind, content, timestamp in rows
        ],
    )


def seed_dashboard(spec: dict) -> None:
    slug, publication_id = spec["slug"], spec.get("publication")
    # Why: adopt_dashboard contrôle les imports sur le dossier local, mais les pages sont servies depuis S3.
    folder = config.INTERACTIVE_DIR / slug
    if spec["has_cron"]:
        folder.mkdir(parents=True, exist_ok=True)
        page = (FIXTURES_DIR / "cron.html").read_text()
        (folder / "index.html").write_text(page.replace("{titre}", spec["title"]).replace("{colonne}", spec["column"]))
        shutil.copy(FIXTURES_DIR / "cron.py", folder / "cron.py")
        subprocess.run([sys.executable, "cron.py"], cwd=folder, check=True, timeout=60)
    else:
        shutil.copytree(FIXTURES_DIR / "dashboards" / slug, folder, dirs_exist_ok=True)
    if "storage" in spec:
        result = query.execute_dashboard_storage_query(sql=spec["storage"], caller=query.CallerType.AGENT)
        if not result.success:
            raise RuntimeError(f"Table de démonstration impossible pour {slug} : {result.error}")
    for path in sorted(folder.rglob("*")):
        if path.is_file() and not s3.interactive.upload(f"{slug}/{path.relative_to(folder)}", path.read_bytes()):
            raise RuntimeError(f"Envoi S3 impossible pour {slug}/{path.relative_to(folder)}")
    if publication_id:
        # Why: identifiant fixe — toutes les review apps partagent le même instantané public au lieu d'en empiler.
        s3.copy_prefix(f"interactive/{slug}/", config.S3_BUCKET, f"publications/{slug}/{publication_id}/")

    adopt_dashboard(
        slug=slug,
        title=spec["title"],
        description=spec["description"],
        website=spec["website"],
        category=spec["category"],
        tags=spec["tags"],
        has_cron=spec["has_cron"],
        has_api_access=spec["has_api_access"],
        has_persistence=spec["has_persistence"],
        first_author_email=spec["owner"],
        created_in_conversation_id=spec.get("created_in"),
    )
    now = datetime.now(timezone.utc)
    with get_db() as session:
        session.execute(update(Dashboard).where(Dashboard.slug == slug).values(is_archived=spec["archived"]))
        for run in spec["cron_runs"]:
            started = now - timedelta(hours=run["hours_ago"])
            session.add(
                CronRun(
                    app_slug=slug,
                    started_at=started,
                    finished_at=started + timedelta(milliseconds=run["duration_ms"]),
                    status=run["status"],
                    output=run["output"],
                    duration_ms=run["duration_ms"],
                    trigger="scheduled",
                )
            )
        if publication_id:
            session.add(
                DashboardPublication(
                    dashboard_slug=slug,
                    publication_id=publication_id,
                    environment="staging",
                    published_by=spec["owner"],
                    published_at=now,
                    snapshot_has_cron=spec["has_cron"],
                )
            )
    if publication_id:
        publications.refresh(publication_id)


def purge() -> None:
    """Supprime le jeu de démonstration ; restent les tags, les fichiers S3 et la table de dashboard_storage, partagés."""
    data = load()
    conversation_ids = [spec["id"] for spec in data["conversations"]]
    slugs = [spec["slug"] for spec in data["dashboards"]]
    # Why: le cron d'une publication tourne sous `<slug>-<publication>` (web/cron.py).
    run_slugs = slugs + [
        f"{spec['slug']}-{spec['publication']}" for spec in data["dashboards"] if "publication" in spec
    ]
    with get_db() as session:
        session.execute(delete(Report).where(Report.source_conversation_id.in_(conversation_ids)))
        session.execute(delete(Message).where(Message.conversation_id.in_(conversation_ids)))
        session.execute(delete(Conversation).where(Conversation.id.in_(conversation_ids)))
        session.execute(delete(CronRun).where(CronRun.app_slug.in_(run_slugs)))
        session.execute(delete(Dashboard).where(Dashboard.slug.in_(slugs)))
        session.execute(delete(PinnedItem).where(PinnedItem.item_id.in_(conversation_ids + slugs)))
        session.execute(delete(UserFavorite).where(UserFavorite.item_id.in_(conversation_ids + slugs)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purge", action="store_true", help="supprime le jeu au lieu de le créer")
    args = parser.parse_args(argv)
    if not config.ENV.seeds_fixtures:
        logger.info("Pas de jeu de démonstration hors review app (AUTOMETA_ENV=%s)", config.ENV)
        return 0
    if args.purge:
        purge()
        return 0
    try:
        seed()
    except Exception:  # Why: des données de démonstration ne doivent jamais bloquer le déploiement d'une review app
        logger.exception("Jeu de démonstration en échec")
        init_sentry()
        sentry_sdk.capture_exception()
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.exit(main())
