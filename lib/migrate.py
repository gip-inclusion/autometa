"""Run alembic migrations on deploy, reporting failures to Sentry."""

import logging
import subprocess
import sys
import time

import sentry_sdk
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from web.db import get_engine
from web.sentry import init_sentry

logger = logging.getLogger(__name__)

# Why: une review app est déployée pendant que son addon Postgres démarre encore
DATABASE_WAIT_SECONDS = 90
DATABASE_RETRY_SECONDS = 3


def wait_for_database(timeout: float = DATABASE_WAIT_SECONDS) -> bool:
    """Attend que la base accepte les connexions, le temps qu'un addon fraîchement créé démarre."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            with get_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except OperationalError as exc:
            if time.monotonic() >= deadline:
                logger.error("database still unreachable after %ss: %s", timeout, exc)
                return False
            logger.info("database not ready yet, retrying in %ss", DATABASE_RETRY_SECONDS)
            time.sleep(DATABASE_RETRY_SECONDS)


def main() -> int:
    if not wait_for_database():
        init_sentry()
        sentry_sdk.capture_message("Deploy migration aborted: database never became reachable", level="error")
        return 1
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
