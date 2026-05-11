"""Create dashboard skill — thin wrapper over lib.dashboards.create_dashboard."""

import argparse
import json
import sys
from datetime import timezone

from lib.dashboards import create_dashboard
from web import config


def _require_runtime_context() -> tuple[str, str]:
    conversation_id = config.agent_conversation_id()
    user_email = config.agent_user_email()
    missing = [
        name
        for name, value in (("AUTOMETA_CONVERSATION_ID", conversation_id), ("AUTOMETA_USER_EMAIL", user_email))
        if not value
    ]
    if missing:
        print(f"Error: missing env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(2)
    return conversation_id, user_email


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new dashboard.")
    parser.add_argument("--slug", required=True, help="Slug (lowercase, kebab-case)")
    parser.add_argument("--title", required=True, help="Display title")
    parser.add_argument("--description", required=True, help="Single-line description")
    parser.add_argument("--website", help="Associated site (emplois, dora, ...)")
    parser.add_argument("--category", help="Free-text category")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--has-cron", action="store_true", help="Include cron.py and set has_cron flag")
    parser.add_argument("--has-api-access", action="store_true", help="Set has_api_access flag")
    parser.add_argument("--has-persistence", action="store_true", help="Set has_persistence flag")
    args = parser.parse_args()

    conversation_id, user_email = _require_runtime_context()

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    try:
        dashboard = create_dashboard(
            slug=args.slug,
            title=args.title,
            description=args.description,
            website=args.website,
            category=args.category,
            tags=tags,
            has_cron=args.has_cron,
            has_api_access=args.has_api_access,
            has_persistence=args.has_persistence,
            first_author_email=user_email,
            created_in_conversation_id=conversation_id,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        json.dumps({
            "slug": dashboard.slug,
            "directory": f"data/interactive/{dashboard.slug}",
            "first_author_email": dashboard.first_author_email,
            "conversation_id": dashboard.created_in_conversation_id,
            "created_at": dashboard.created_at.astimezone(timezone.utc).isoformat(),
        })
    )


if __name__ == "__main__":
    main()
