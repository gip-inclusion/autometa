"""Contexte du backlog, rangé dans dashboard_storage et rafraîchi périodiquement."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import Column, DateTime, MetaData, String, Table, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import ProgrammingError

from lib import backlog
from web import config
from web.db import get_engine

logger = logging.getLogger(__name__)

SCHEMA = "dashboard_storage"

_metadata = MetaData(schema=SCHEMA)
backlog_context = Table(
    "backlog_context",
    _metadata,
    Column("key", String, primary_key=True),
    Column("content", JSONB, nullable=False),
    Column("generated_at", DateTime(timezone=True), nullable=False),
)


def ensure_schema() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS " + SCHEMA))
    _metadata.create_all(engine)


def save_context(context: dict) -> None:
    """Range le contexte, sauf si un chargement plus récent est déjà rangé."""
    ensure_schema()
    statement = pg_insert(backlog_context).values(
        key="current", content=context, generated_at=datetime.fromisoformat(context["generated_at"])
    )
    statement = statement.on_conflict_do_update(
        index_elements=["key"],
        set_={"content": statement.excluded.content, "generated_at": statement.excluded.generated_at},
        where=backlog_context.c.generated_at < statement.excluded.generated_at,
    )
    with get_engine().begin() as conn:
        conn.execute(statement)


def read_context() -> dict | None:
    """Le contexte rangé s'il a moins de 30 heures, sinon None."""
    try:
        with get_engine().connect() as conn:
            row = conn.execute(
                select(backlog_context.c.content, backlog_context.c.generated_at).where(
                    backlog_context.c.key == "current"
                )
            ).first()
    except ProgrammingError as error:
        # Why: seule la table absente (première lecture avant toute écriture) est attendue ; le reste remonte.
        if error.orig.pgcode != "42P01":
            raise
        return None
    # Why: le cron tourne chaque jour ; 24 h strictes laisseraient un trou chaque nuit, et un cron en échec
    # renverrait toutes les conversations vers Notion.
    if row is None or datetime.now(UTC) - row.generated_at > timedelta(hours=30):
        return None
    return row.content


def current_context() -> dict:
    """Le contexte rangé s'il est frais, sinon un contexte relu dans Notion, puis rangé."""
    context = read_context()
    if context is None:
        context = backlog.load_context()
        save_context(context)
    return context


def main() -> None:
    """Point d'entrée du cron."""
    if not config.NOTION_BACKLOG_DB:
        logger.warning("NOTION_BACKLOG_DB absent : contexte du backlog non rafraîchi")
        return
    context = backlog.load_context()
    save_context(context)
    logger.info("Contexte du backlog rangé : %d équipes", len(context["teams"]))
