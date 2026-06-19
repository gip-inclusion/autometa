"""Run alembic migrations on deploy, reporting failures to Sentry."""

import logging
import subprocess
import sys

import sentry_sdk

from web.sentry import init_sentry

logger = logging.getLogger(__name__)


def main() -> int:
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
