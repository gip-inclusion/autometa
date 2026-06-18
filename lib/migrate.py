"""Run alembic migrations, auto-stamping head when the schema predates alembic."""

import logging
import subprocess
import sys

import sentry_sdk
from sqlalchemy import create_engine, inspect

from web import config
from web.sentry import init_sentry

logger = logging.getLogger(__name__)


def needs_stamp(database_url: str) -> bool:
    engine = create_engine(database_url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    return "conversations" in tables and "alembic_version" not in tables


def main() -> int:
    if needs_stamp(config.DATABASE_URL):
        logger.warning("Existing schema without alembic_version, stamping to head")
        subprocess.run(["alembic", "stamp", "head"], check=True)

    result = subprocess.run(["alembic", "upgrade", "head"])
    if result.returncode != 0:
        logger.error("alembic upgrade head failed (exit code %s)", result.returncode)
        init_sentry()
        try:
            sentry_sdk.capture_message(
                f"Deploy migration failed: alembic upgrade head exited {result.returncode}",
                level="error",
            )
        except Exception:  # Why: never let alerting failure mask the original migration failure
            logger.exception("failed to report migration failure to Sentry")
    return result.returncode


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.exit(main())
