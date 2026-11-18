"""Tables des modules dans le schéma dashboard_storage, créées hors Alembic."""

from sqlalchemy import MetaData, text

from web.db import get_engine


def create_tables(metadata: MetaData) -> None:
    """Crée le schéma de metadata s'il manque, puis celles de ses tables qui manquent."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS " + metadata.schema))
    metadata.create_all(engine)
