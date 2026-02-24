#!/usr/bin/env python3
"""Migrate SQLite data to PostgreSQL + S3 for Scalingo deployment.

Reads from local data-remote/ (synced from production server) and writes to:
- PostgreSQL (via DATABASE_URL)
- S3 bucket (via S3_* env vars)

Usage:
    # Set target env vars, then:
    .venv/bin/python scripts/migrate_to_scalingo.py

    # Dry run (prints what would be done):
    .venv/bin/python scripts/migrate_to_scalingo.py --dry-run

    # Skip S3 upload (DB only):
    .venv/bin/python scripts/migrate_to_scalingo.py --db-only

    # Skip DB (S3 only):
    .venv/bin/python scripts/migrate_to_scalingo.py --s3-only
"""

import argparse
import mimetypes
import os
import sqlite3
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data-remote"
SQLITE_PATH = DATA_DIR / "matometa.db"

# Tables to migrate, in insertion order (respects FK constraints)
TABLES = [
    "schema_version",
    "conversations",
    "messages",
    "tags",
    "reports",
    "conversation_tags",
    "report_tags",
    "uploaded_files",
    "pinned_items",
    "cron_runs",
    "pm_commands",
    "pm_heartbeat",
]


# ---------------------------------------------------------------------------
# Database migration
# ---------------------------------------------------------------------------

def migrate_db(database_url: str, dry_run: bool = False):
    """Migrate all tables from SQLite to PostgreSQL."""
    src = sqlite3.connect(str(SQLITE_PATH))
    src.row_factory = sqlite3.Row

    if dry_run:
        # Dry run: just count rows from SQLite, no PG connection needed
        print("  [dry-run] Would create schema.\n")
        for table in TABLES:
            src_tables = [
                r[0] for r in src.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
            if table not in src_tables:
                print(f"  {table}: not in source, skipping")
                continue
            count = src.execute(f"SELECT COUNT(*) as c FROM [{table}]").fetchone()["c"]
            print(f"  {table}: {count} rows (would insert)")
        print("\n[dry-run] No changes made to DB.")
        src.close()
        return

    import psycopg2
    from psycopg2.extras import execute_values

    # Let the app create the schema (init_db)
    print("Initializing PG schema via app...")
    os.environ["DATABASE_URL"] = database_url
    from web.schema import init_db
    init_db()
    print("  Schema created.")

    dst = psycopg2.connect(database_url)
    dst.autocommit = False
    cur = dst.cursor()

    try:
        for table in TABLES:
            # Check if table exists in source
            src_tables = [
                r[0] for r in src.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
            if table not in src_tables:
                print(f"  {table}: not in source, skipping")
                continue

            rows = src.execute(f"SELECT * FROM [{table}]").fetchall()
            if not rows:
                print(f"  {table}: 0 rows, skipping")
                continue

            columns = rows[0].keys()
            # Skip sqlite_sequence-style columns
            columns = [c for c in columns if c != "rowid"]

            col_list = ", ".join(columns)
            placeholders = ", ".join(["%s"] * len(columns))

            # Clear target table
            cur.execute(f"DELETE FROM {table}")

            values = [tuple(row[c] for c in columns) for row in rows]

            insert_sql = f"INSERT INTO {table} ({col_list}) VALUES %s"
            execute_values(cur, insert_sql, values, page_size=500)
            print(f"  {table}: {len(values)} rows inserted")

        # Fix serial sequences (PG SERIAL needs to know the max id)
        serial_tables = [
            "messages", "tags", "reports", "uploaded_files",
            "pinned_items", "cron_runs", "pm_commands",
        ]
        for table in serial_tables:
            cur.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"COALESCE(MAX(id), 0) + 1, false) FROM {table}"
            )
            print(f"  {table}: sequence reset")

        dst.commit()
        print("\nDB migration committed.")

    except Exception:
        dst.rollback()
        raise
    finally:
        cur.close()
        dst.close()
        src.close()


# ---------------------------------------------------------------------------
# S3 migration
# ---------------------------------------------------------------------------

def migrate_s3(dry_run: bool = False):
    """Upload interactive/ and uploads/ directories to S3."""
    import boto3
    from botocore.config import Config as BotoConfig

    bucket = os.environ["S3_BUCKET"]
    endpoint = os.environ.get("S3_ENDPOINT")
    access_key = os.environ["S3_ACCESS_KEY"]
    secret_key = os.environ["S3_SECRET_KEY"]
    region = os.environ.get("S3_REGION", "fr-par")
    prefix = os.environ.get("S3_PREFIX", "interactive/")

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=BotoConfig(signature_version="s3v4"),
    )

    # 1. Interactive files → S3 under S3_PREFIX (default: interactive/)
    interactive_dir = DATA_DIR / "interactive"
    if interactive_dir.exists():
        files = sorted(f for f in interactive_dir.rglob("*") if f.is_file())
        print(f"\nInteractive files: {len(files)} files")
        for f in files:
            rel = f.relative_to(interactive_dir)
            key = f"{prefix}{rel}"
            content_type, _ = mimetypes.guess_type(str(f))
            content_type = content_type or "application/octet-stream"

            if dry_run:
                print(f"  [dry-run] {key} ({f.stat().st_size:,} bytes)")
            else:
                client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=f.read_bytes(),
                    ContentType=content_type,
                )
                print(f"  {key} ({f.stat().st_size:,} bytes)")

    # 2. Uploaded files → S3 under uploads/ prefix
    #    (uploads.py uses "uploads/{stored_filename}" as the key)
    uploads_dir = DATA_DIR / "uploads"
    if uploads_dir.exists():
        files = sorted(f for f in uploads_dir.rglob("*") if f.is_file())
        print(f"\nUpload files: {len(files)} files")
        for f in files:
            rel = f.relative_to(uploads_dir)
            # s3 module uses "interactive/" prefix, but uploads.py prepends "uploads/"
            # so the full key is: interactive/uploads/{filename}
            key = f"{prefix}uploads/{rel}"
            content_type, _ = mimetypes.guess_type(str(f))
            content_type = content_type or "application/octet-stream"

            if dry_run:
                print(f"  [dry-run] {key} ({f.stat().st_size:,} bytes)")
            else:
                client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=f.read_bytes(),
                    ContentType=content_type,
                )
                print(f"  {key} ({f.stat().st_size:,} bytes)")

    if dry_run:
        print("\n[dry-run] No files uploaded to S3.")
    else:
        print("\nS3 migration done.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite → PostgreSQL + S3")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done")
    parser.add_argument("--db-only", action="store_true", help="Only migrate database")
    parser.add_argument("--s3-only", action="store_true", help="Only migrate files to S3")
    args = parser.parse_args()

    if not SQLITE_PATH.exists():
        # Try downloading from S3 (for running inside Scalingo one-off)
        if os.environ.get("S3_BUCKET"):
            print(f"SQLite DB not found locally, downloading from S3...")
            import boto3
            from botocore.config import Config as BotoConfig
            client = boto3.client(
                "s3",
                endpoint_url=os.environ.get("S3_ENDPOINT"),
                aws_access_key_id=os.environ["S3_ACCESS_KEY"],
                aws_secret_access_key=os.environ["S3_SECRET_KEY"],
                region_name=os.environ.get("S3_REGION", "fr-par"),
                config=BotoConfig(signature_version="s3v4"),
            )
            SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(os.environ["S3_BUCKET"], "_migration/matometa.db", str(SQLITE_PATH))
            print(f"  Downloaded to {SQLITE_PATH} ({SQLITE_PATH.stat().st_size:,} bytes)")
        else:
            print(f"ERROR: SQLite database not found at {SQLITE_PATH}")
            print("Run: rsync -avz matometa@ljt.cc:/srv/matometa/data/ ./data-remote/")
            sys.exit(1)

    do_db = not args.s3_only
    do_s3 = not args.db_only

    if do_db:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            print("ERROR: DATABASE_URL not set. Get it from Scalingo:")
            print("  scalingo --app matometa env | grep DATABASE_URL")
            sys.exit(1)
        print(f"=== DB Migration (SQLite → PostgreSQL) ===")
        print(f"Source: {SQLITE_PATH}")
        print(f"Target: {database_url.split('@')[1] if '@' in database_url else database_url}")
        migrate_db(database_url, dry_run=args.dry_run)

    if do_s3:
        if not os.environ.get("S3_BUCKET"):
            print("ERROR: S3_BUCKET not set.")
            sys.exit(1)
        print(f"\n=== S3 Migration (files → {os.environ['S3_BUCKET']}) ===")
        print(f"Source: {DATA_DIR}")
        migrate_s3(dry_run=args.dry_run)

    print("\nDone!")


if __name__ == "__main__":
    main()
