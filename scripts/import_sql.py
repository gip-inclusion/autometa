#!/usr/bin/env python3
"""Download migration.sql from S3 and import into PostgreSQL.

Run on Scalingo one-off:
    scalingo --app matometa run python scripts/import_sql.py
"""
import os
import re
import sys

import boto3
from botocore.config import Config as BotoConfig
import psycopg2

SQL_KEY = "_migration/migration.sql"
LOCAL_PATH = "/tmp/migration.sql"


def main():
    # Download from S3
    print("Downloading migration.sql from S3...")
    client = boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT"),
        aws_access_key_id=os.environ["S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["S3_SECRET_KEY"],
        region_name=os.environ.get("S3_REGION", "fr-par"),
        config=BotoConfig(signature_version="s3v4"),
    )
    client.download_file(os.environ["S3_BUCKET"], SQL_KEY, LOCAL_PATH)
    size = os.path.getsize(LOCAL_PATH)
    print(f"  Downloaded: {size:,} bytes")

    # Import into PG
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("SCALINGO_POSTGRESQL_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    # Split SQL into per-table sections to avoid connection timeout
    sql = open(LOCAL_PATH).read()
    # Split on comment headers like "-- tablename: N rows"
    sections = re.split(r'(?=^-- \w+:)', sql, flags=re.MULTILINE)

    print(f"Connecting to PostgreSQL...")
    conn = psycopg2.connect(database_url)
    conn.autocommit = True  # each section is its own transaction

    for section in sections:
        section = section.strip()
        if not section or section.startswith("-- SQLite"):
            continue

        # Extract table name from comment
        header = section.split('\n')[0]
        print(f"  {header}")

        cur = conn.cursor()
        try:
            cur.execute(section)
        except Exception as e:
            print(f"  ERROR: {e}")
            # Continue with other tables
        finally:
            cur.close()

    conn.close()

    # Verify
    print("\nVerification:")
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    for table in ["conversations", "messages", "tags", "reports", "uploaded_files", "pinned_items"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table}: {count} rows")
    cur.close()
    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
