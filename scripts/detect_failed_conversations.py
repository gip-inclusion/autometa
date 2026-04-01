#!/usr/bin/env python3
"""Detect conversations where Autometa likely failed (errors, corrections, omissions)."""

import argparse
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from lib.failure_detection import FAILURE_MARKERS, extract_snippet
from lib.slack import lookup_user as slack_lookup_user
from lib.slack import send_dm as slack_send_dm
from web import config
from web.db import get_db
from web.schema import init_db

NOTIFY_EMAILS = config.FAILURE_NOTIFY_EMAILS

# FIXME(vperron): this file seems unused ?


def get_failed_conversations(days: int) -> list[dict]:
    init_db()

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")

    like_clauses = " OR ".join([f"LOWER(m.content) LIKE :m{i}" for i in range(len(FAILURE_MARKERS))])
    params = {f"m{i}": f"%{marker}%" for i, marker in enumerate(FAILURE_MARKERS)}
    params["cutoff"] = cutoff

    sql = text(f"""
        SELECT DISTINCT c.id, c.title, m.content
        FROM conversations c
        JOIN messages m ON m.conversation_id = c.id
        WHERE m.role = 'assistant'
          AND c.updated_at >= :cutoff
          AND ({like_clauses})
        ORDER BY c.updated_at DESC
    """)

    with get_db() as session:
        rows = session.execute(sql, params).mappings().all()

    # Deduplicate by conversation id, keep first match
    seen = set()
    results = []
    for row in rows:
        conv_id = row["id"]
        if conv_id in seen:
            continue
        seen.add(conv_id)
        snip = extract_snippet(row["content"])
        results.append({
            "id": conv_id,
            "title": row["title"] or "Sans titre",
            "snippet": snip,
        })

    return results


def build_slack_message(conversations: list[dict]) -> str:
    base_url = config.BASE_URL

    lines = [":mag: *Conversations à vérifier*\n"]
    for conv in conversations:
        url = f"{base_url}/explorations/{conv['id']}"
        title = conv["title"]
        snippet = conv["snippet"]
        lines.append(f'• <{url}|{title}> — "{snippet}"')

    lines.append(f"\n{len(conversations)} conversation(s) détectée(s)")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Detect failed conversations")
    parser.add_argument("--dry-run", action="store_true", help="List detected conversations without sending")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back (default: 7)")
    args = parser.parse_args()

    conversations = get_failed_conversations(args.days)
    print(f"Found {len(conversations)} conversation(s) with failure markers (last {args.days} days)")

    if not conversations:
        print("Nothing to report.")
        return

    if args.dry_run:
        for conv in conversations:
            print(f'  [{conv["id"][:8]}] {conv["title"]} — "{conv["snippet"]}"')
        print("\nSlack message preview:\n")
        print(build_slack_message(conversations))
        return

    token = config.SLACK_BOT_TOKEN
    if not token:
        print("ERROR: SLACK_BOT_TOKEN is not set", file=sys.stderr)
        sys.exit(1)

    if not NOTIFY_EMAILS:
        print("ERROR: FAILURE_NOTIFY_EMAILS is not set", file=sys.stderr)
        sys.exit(1)

    message = build_slack_message(conversations)
    for email in NOTIFY_EMAILS:
        slack_id = slack_lookup_user(token, email)
        if not slack_id:
            print(f"WARNING: Could not find Slack user for {email}", file=sys.stderr)
            continue
        ok = slack_send_dm(token, slack_id, message)
        if ok:
            print(f"Slack DM sent to {email}")
        else:
            print(f"FAILED to send Slack DM to {email}", file=sys.stderr)


if __name__ == "__main__":
    main()
