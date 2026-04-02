"""Per-app database provisioning on shared Scaleway Managed PostgreSQL."""

import logging
import secrets
import string

from web import config

logger = logging.getLogger(__name__)


def available() -> bool:
    """True if managed PG credentials are configured."""
    return bool(config.SCW_RDB_HOST and config.SCW_RDB_ADMIN_USER and config.SCW_RDB_ADMIN_PASSWORD)


def _admin_connect():
    """Connect to the managed PG instance as admin."""
    import psycopg2
    return psycopg2.connect(
        host=config.SCW_RDB_HOST,
        port=int(config.SCW_RDB_PORT),
        user=config.SCW_RDB_ADMIN_USER,
        password=config.SCW_RDB_ADMIN_PASSWORD,
        dbname="postgres",
        sslmode="require",
        connect_timeout=10,
    )


def _random_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_app_database(slug: str) -> dict:
    """Create a dedicated database + user for an app.

    DB name: matometa_{slug}  (hyphens replaced with underscores)
    User:    matometa_{slug}
    Password: random 24-char

    Returns {"status": "ok", "database_url": "postgresql://...", "db_name": ..., "db_user": ...}
         or {"status": "error", "error": "...", "step": "connect|create_user|create_db|grant"}
    """
    safe_slug = slug.replace("-", "_")
    db_name = f"matometa_{safe_slug}"
    db_user = f"matometa_{safe_slug}"
    db_password = _random_password()

    try:
        conn = _admin_connect()
    except Exception as e:
        return {"status": "error", "error": str(e), "step": "connect"}

    conn.autocommit = True
    cur = conn.cursor()

    try:
        # Create user (skip if exists)
        cur.execute(f"SELECT 1 FROM pg_roles WHERE rolname = %s", (db_user,))
        if not cur.fetchone():
            cur.execute(f'CREATE USER "{db_user}" WITH PASSWORD %s', (db_password,))
        else:
            # Reset password for existing user
            cur.execute(f'ALTER USER "{db_user}" WITH PASSWORD %s', (db_password,))
    except Exception as e:
        conn.close()
        return {"status": "error", "error": str(e), "step": "create_user"}

    try:
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{db_name}"')
    except Exception as e:
        conn.close()
        return {"status": "error", "error": str(e), "step": "create_db"}

    try:
        cur.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{db_name}" TO "{db_user}"')
    except Exception as e:
        conn.close()
        return {"status": "error", "error": str(e), "step": "grant"}

    conn.close()

    database_url = (
        f"postgresql://{db_user}:{db_password}@"
        f"{config.SCW_RDB_HOST}:{config.SCW_RDB_PORT}/{db_name}?sslmode=require"
    )

    logger.info("Created database %s for app %s", db_name, slug)
    return {
        "status": "ok",
        "database_url": database_url,
        "db_name": db_name,
        "db_user": db_user,
    }


def delete_app_database(slug: str) -> dict:
    """Drop database and user for an app.

    Returns {"status": "ok"} or {"status": "error", "error": "...", "step": "..."}
    """
    safe_slug = slug.replace("-", "_")
    db_name = f"matometa_{safe_slug}"
    db_user = f"matometa_{safe_slug}"

    try:
        conn = _admin_connect()
    except Exception as e:
        return {"status": "error", "error": str(e), "step": "connect"}

    conn.autocommit = True
    cur = conn.cursor()

    try:
        # Terminate active connections
        cur.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
            (db_name,)
        )
        cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        cur.execute(f'DROP USER IF EXISTS "{db_user}"')
    except Exception as e:
        conn.close()
        return {"status": "error", "error": str(e), "step": "drop"}

    conn.close()
    logger.info("Deleted database %s", db_name)
    return {"status": "ok"}
