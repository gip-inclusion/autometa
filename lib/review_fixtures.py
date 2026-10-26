"""Jeu de démonstration des review apps : conversations et tableaux de bord typiques, sans donnée réelle."""

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, insert, select, update

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
    Report,
    Tag,
)

logger = logging.getLogger(__name__)

FIXTURES_DIR = config.BASE_DIR / "fixtures" / "review"


def load() -> dict:
    return json.loads((FIXTURES_DIR / "fixtures.json").read_text())


def owner(name: str) -> str:
    """« admin » désigne le premier administrateur configuré : aucune adresse réelle dans le dépôt."""
    return config.ADMIN_USERS[0] if name == "admin" else name


def seed() -> None:
    data = load()
    with get_db() as session:
        known = set(session.scalars(select(Tag.name)))
        session.add_all(Tag(**tag) for tag in data["tags"] if tag["name"] not in known)
        session.flush()
        for spec in data["conversations"]:
            if session.get(Conversation, spec["id"]) is None:
                seed_conversation(session, spec)
    for spec in data["dashboards"]:
        seed_dashboard(spec)


def seed_conversation(session, spec: dict) -> None:
    user = owner(spec["owner"])
    created = datetime.now(timezone.utc) - timedelta(days=spec["days_ago"])
    source = select(Message.type, Message.content).where(Message.conversation_id == spec.get("forked_from"))
    copied = session.execute(source.order_by(Message.id)).all() if "forked_from" in spec else []
    turns = [(kind, body, n) for n in range(1, spec.get("repeat", 1) + 1) for kind, body in spec["messages"]]
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
            updated_at=created + timedelta(seconds=20 * (len(copied) + len(turns))),
        )
    )
    session.flush()
    tag_ids = session.scalars(select(Tag.id).where(Tag.name.in_(spec["tags"])))
    session.add_all(ConversationTag(conversation_id=spec["id"], tag_id=tag_id) for tag_id in tag_ids)

    rows = list(copied)
    for kind, body, n in turns:
        if kind == "report":
            report = Report(
                **body, source_conversation_id=spec["id"], user_id=user, created_at=created, updated_at=created
            )
            session.add(report)
            session.flush()
            body = {"report_id": report.id, "title": report.title}
        content = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
        rows.append((kind, content.replace("{n}", str(n))))
    session.execute(
        insert(Message),
        [
            {
                "conversation_id": spec["id"],
                "type": kind,
                "role": kind,
                "content": content,
                "timestamp": created + timedelta(seconds=20 * i),
            }
            for i, (kind, content) in enumerate(rows)
        ],
    )


def seed_dashboard(spec: dict) -> None:
    slug = spec["slug"]
    with get_db() as session:
        if session.scalar(select(Dashboard.id).where(Dashboard.slug == slug)) is not None:
            return

    # Why: adopt_dashboard contrôle les imports sur le dossier local, mais les pages sont servies depuis S3.
    folder = config.INTERACTIVE_DIR / slug
    shutil.copytree(FIXTURES_DIR / "dashboards" / slug, folder, dirs_exist_ok=True)
    if spec["has_cron"]:
        shutil.copy(FIXTURES_DIR / "cron.py", folder / "cron.py")
    for path in sorted(folder.rglob("*")):
        if path.is_file() and not s3.interactive.upload(f"{slug}/{path.relative_to(folder)}", path.read_bytes()):
            raise RuntimeError(f"Envoi S3 impossible pour {slug}/{path.relative_to(folder)}")

    author = owner(spec["owner"])
    adopt_dashboard(
        slug=slug,
        title=spec["title"],
        description=spec["description"],
        website=spec["website"],
        category=spec["category"],
        tags=spec["tags"],
        has_cron=spec["has_cron"],
        has_api_access=spec["has_api_access"],
        first_author_email=author,
        created_in_conversation_id=spec.get("created_in"),
    )
    now = datetime.now(timezone.utc)
    publication_id = spec.get("publication")
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
                    published_by=author,
                    published_at=now,
                    snapshot_has_cron=spec["has_cron"],
                )
            )
    if publication_id:
        # Why: identifiant fixe — toutes les review apps partagent le même instantané public au lieu d'en empiler.
        s3.copy_prefix(f"interactive/{slug}/", config.S3_BUCKET, f"publications/{slug}/{publication_id}/")
        publications.refresh(publication_id)


def purge() -> None:
    """Supprime le jeu de démonstration ; les fichiers S3, partagés entre review apps, restent en place."""
    data = load()
    conversation_ids = [spec["id"] for spec in data["conversations"]]
    slugs = [spec["slug"] for spec in data["dashboards"]]
    with get_db() as session:
        session.execute(delete(Report).where(Report.source_conversation_id.in_(conversation_ids)))
        session.execute(delete(Message).where(Message.conversation_id.in_(conversation_ids)))
        session.execute(delete(Conversation).where(Conversation.id.in_(conversation_ids)))
        session.execute(delete(CronRun).where(CronRun.app_slug.in_(slugs)))
        session.execute(delete(Dashboard).where(Dashboard.slug.in_(slugs)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purge", action="store_true", help="supprime le jeu au lieu de le créer")
    args = parser.parse_args(argv)
    if not config.ENV.seeds_fixtures:
        logger.info("Pas de jeu de démonstration hors review app (AUTOMETA_ENV=%s)", config.ENV)
        return 0
    if args.purge:
        purge()
    else:
        seed()
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.exit(main())
