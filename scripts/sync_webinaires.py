#!/usr/bin/env python3
"""Sync webinaire attendance data from Livestorm and Grist into SQLite.

Usage:
    python scripts/sync_webinaires.py                  # Full sync (both sources)
    python scripts/sync_webinaires.py --grist-only     # Grist only (for daily cron)
    python scripts/sync_webinaires.py --livestorm-only  # Livestorm only
    python scripts/sync_webinaires.py --db PATH         # Custom DB path
"""

import argparse
import logging
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.webinaires import (
    DEFAULT_DB_PATH,
    GristClient,
    LivestormClient,
    ensure_schema,
    sync_grist,
    sync_livestorm,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    parser = argparse.ArgumentParser(description="Sync webinaire attendance data")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH,
                        help="SQLite database path")
    parser.add_argument("--grist-only", action="store_true",
                        help="Only sync Grist (for daily cron)")
    parser.add_argument("--livestorm-only", action="store_true",
                        help="Only sync Livestorm")
    args = parser.parse_args()

    args.db.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 50)
    print("WEBINAIRES SYNC")
    print("=" * 50)
    print(f"Database: {args.db}")
    print(f"Mode: {'grist-only' if args.grist_only else 'livestorm-only' if args.livestorm_only else 'full'}")
    print()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    t0 = time.time()
    results = {}

    # Livestorm sync
    if not args.grist_only:
        print("=" * 50)
        print("LIVESTORM SYNC")
        print("=" * 50)
        try:
            client = LivestormClient()
            events, sessions, regs = sync_livestorm(conn, client)
            results["livestorm"] = {
                "events": events,
                "sessions": sessions,
                "registrations": regs,
                "api_calls": client.request_count,
                "monthly_remaining": client.monthly_remaining,
            }
            print(f"\n  Livestorm: {events} events, {sessions} sessions, "
                  f"{regs} registrations, {client.request_count} API calls")
            if client.monthly_remaining is not None:
                print(f"  Monthly API budget remaining: {client.monthly_remaining}")
        except Exception as e:
            print(f"\n  ERROR: Livestorm sync failed: {e}")
            results["livestorm"] = {"error": str(e)}
        print()

    # Grist sync
    if not args.livestorm_only:
        print("=" * 50)
        print("GRIST SYNC")
        print("=" * 50)
        try:
            client = GristClient()
            webinaires, regs = sync_grist(conn, client)
            results["grist"] = {
                "webinaires": webinaires,
                "registrations": regs,
                "api_calls": client.request_count,
            }
            print(f"\n  Grist: {webinaires} webinaires, {regs} registrations")
        except Exception as e:
            print(f"\n  ERROR: Grist sync failed: {e}")
            results["grist"] = {"error": str(e)}
        print()

    # Store sync metadata
    total_time = time.time() - t0
    now = datetime.now(tz=timezone.utc).isoformat()

    total_webinars = conn.execute("SELECT COUNT(*) FROM webinars").fetchone()[0]
    total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    total_regs = conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0]
    unique_emails = conn.execute(
        "SELECT COUNT(DISTINCT email) FROM registrations"
    ).fetchone()[0]

    conn.execute("INSERT OR REPLACE INTO sync_meta VALUES (?, ?)",
                 ("last_sync", now))
    conn.execute("INSERT OR REPLACE INTO sync_meta VALUES (?, ?)",
                 ("sync_duration_seconds", str(round(total_time, 1))))
    conn.execute("INSERT OR REPLACE INTO sync_meta VALUES (?, ?)",
                 ("total_webinars", str(total_webinars)))
    conn.execute("INSERT OR REPLACE INTO sync_meta VALUES (?, ?)",
                 ("total_sessions", str(total_sessions)))
    conn.execute("INSERT OR REPLACE INTO sync_meta VALUES (?, ?)",
                 ("total_registrations", str(total_regs)))
    conn.execute("INSERT OR REPLACE INTO sync_meta VALUES (?, ?)",
                 ("unique_emails", str(unique_emails)))
    conn.commit()
    conn.close()

    # Summary
    db_size = args.db.stat().st_size / 1024 / 1024
    print("=" * 50)
    print("SYNC COMPLETE")
    print("=" * 50)
    print(f"Total time:      {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"Webinars:        {total_webinars}")
    print(f"Sessions:        {total_sessions}")
    print(f"Registrations:   {total_regs}")
    print(f"Unique emails:   {unique_emails}")
    print(f"DB size:         {db_size:.1f} MB")

    # Exit with error if any source failed
    for source, info in results.items():
        if "error" in info:
            sys.exit(1)


if __name__ == "__main__":
    main()
