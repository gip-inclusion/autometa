"""Contexte des équipes du backlog, rangé dans dashboard_storage et rafraîchi chaque jour."""

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
backlog_contexte = Table(
    "backlog_contexte",
    _metadata,
    Column("cle", String, primary_key=True),
    Column("contenu", JSONB, nullable=False),
    Column("genere_le", DateTime(timezone=True), nullable=False),
)


def ensure_schema() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS " + SCHEMA))
    _metadata.create_all(engine)


def enregistrer_contexte(contexte: dict) -> None:
    """Range le contexte, sauf si un chargement plus récent est déjà rangé."""
    ensure_schema()
    statement = pg_insert(backlog_contexte).values(
        cle="courant", contenu=contexte, genere_le=datetime.fromisoformat(contexte["genere_le"])
    )
    statement = statement.on_conflict_do_update(
        index_elements=["cle"],
        set_={"contenu": statement.excluded.contenu, "genere_le": statement.excluded.genere_le},
        where=backlog_contexte.c.genere_le < statement.excluded.genere_le,
    )
    with get_engine().begin() as conn:
        conn.execute(statement)


# Why: le cron tourne chaque jour ; 24 h strictes laisseraient un trou chaque nuit, et un cron en échec
# renverrait toutes les conversations vers Notion.
def lire_contexte(age_max: timedelta = timedelta(hours=30)) -> dict | None:
    """Le contexte rangé s'il a moins de age_max, sinon None."""
    try:
        with get_engine().connect() as conn:
            ligne = conn.execute(
                select(backlog_contexte.c.contenu, backlog_contexte.c.genere_le).where(
                    backlog_contexte.c.cle == "courant"
                )
            ).first()
    except ProgrammingError:
        # Why: première lecture avant toute écriture, la table n'existe pas encore.
        return None
    if ligne is None or datetime.now(UTC) - ligne.genere_le > age_max:
        return None
    return ligne.contenu


def contexte_courant() -> dict:
    """Le contexte rangé s'il est frais, sinon un contexte relu dans Notion, puis rangé."""
    contexte = lire_contexte()
    if contexte is None:
        contexte = backlog.charger_contexte()
        enregistrer_contexte(contexte)
    return contexte


def main() -> None:
    """Point d'entrée du cron quotidien."""
    if not config.NOTION_BACKLOG_DB:
        logger.warning("NOTION_BACKLOG_DB absent : contexte du backlog non rafraîchi")
        return
    contexte = backlog.charger_contexte()
    enregistrer_contexte(contexte)
    logger.info("Contexte du backlog rangé : %d équipes", len(contexte["equipes"]))
