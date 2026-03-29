#!/usr/bin/env python3
"""Sync webinaire attendance data from Livestorm and Grist into datalake."""

import logging
import sys
import time
from datetime import datetime, timezone

from lib.webinaires import (
    T_INSCRIPTIONS,
    T_SYNC_META,
    T_WEBINAIRES,
    DatalakeWriter,
    GristClient,
    LivestormClient,
    sync_grist,
    sync_livestorm,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")


def main():
    conn = DatalakeWriter()
    t0 = time.time()
    results = {}

    print("--- Livestorm ---")
    try:
        client = LivestormClient()
        events, sessions, regs = sync_livestorm(conn, client)
        results["livestorm"] = {"events": events, "sessions": sessions, "registrations": regs}
        print(f"  {events} events, {sessions} sessions, {regs} registrations")
    except Exception as e:
        print(f"  ERROR: {e}")
        results["livestorm"] = {"error": str(e)}

    print("--- Grist ---")
    try:
        client = GristClient()
        webinaires, regs = sync_grist(conn, client)
        results["grist"] = {"webinaires": webinaires, "registrations": regs}
        print(f"  {webinaires} webinaires, {regs} registrations")
    except Exception as e:
        print(f"  ERROR: {e}")
        results["grist"] = {"error": str(e)}

    total_time = time.time() - t0
    now = datetime.now(tz=timezone.utc).isoformat()

    total_webinars = conn.execute(f"SELECT COUNT(*) FROM {T_WEBINAIRES}").fetchone()[0]
    total_regs = conn.execute(f"SELECT COUNT(*) FROM {T_INSCRIPTIONS}").fetchone()[0]

    for key, value in [
        ("last_sync", now),
        ("sync_duration_seconds", str(round(total_time, 1))),
        ("total_webinars", str(total_webinars)),
        ("total_registrations", str(total_regs)),
    ]:
        conn.execute(
            f"""INSERT INTO {T_SYNC_META} (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            (key, value),
        )

    print(f"\nDone in {total_time:.0f}s — {total_webinars} webinars, {total_regs} registrations")

    for info in results.values():
        if "error" in info:
            sys.exit(1)


if __name__ == "__main__":
    main()
