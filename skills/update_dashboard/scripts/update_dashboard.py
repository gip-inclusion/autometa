"""Update dashboard skill — thin wrapper over lib.dashboards.update_dashboard."""

import argparse
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from lib.dashboards import DashboardNotFound, update_dashboard  # noqa: E402
from web import config  # noqa: E402


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


def _bool_arg(value: str) -> bool:
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False
    raise argparse.ArgumentTypeError(f"expected true|false, got {value!r}")


def _csv(value: str) -> list[str]:
    return [t.strip() for t in value.split(",") if t.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Update an existing dashboard.")
    parser.add_argument("--slug", required=True, help="Slug of the dashboard to update")
    parser.add_argument("--title")
    parser.add_argument("--description")
    parser.add_argument("--website")
    parser.add_argument("--category")
    parser.add_argument("--add-tags", type=_csv, default=None)
    parser.add_argument("--remove-tags", type=_csv, default=None)
    parser.add_argument("--set-tags", type=_csv, default=None)
    parser.add_argument("--has-cron", type=_bool_arg, default=None)
    parser.add_argument("--has-api-access", type=_bool_arg, default=None)
    parser.add_argument("--has-persistence", type=_bool_arg, default=None)
    archive_group = parser.add_mutually_exclusive_group()
    archive_group.add_argument("--archive", action="store_true")
    archive_group.add_argument("--unarchive", action="store_true")
    args = parser.parse_args()

    conversation_id, user_email = _require_runtime_context()

    is_archived: bool | None = None
    if args.archive:
        is_archived = True
    elif args.unarchive:
        is_archived = False

    try:
        result = update_dashboard(
            slug=args.slug,
            updater_email=user_email,
            in_conversation_id=conversation_id,
            title=args.title,
            description=args.description,
            website=args.website,
            category=args.category,
            add_tags=args.add_tags,
            remove_tags=args.remove_tags,
            set_tags=args.set_tags,
            has_cron=args.has_cron,
            has_api_access=args.has_api_access,
            has_persistence=args.has_persistence,
            is_archived=is_archived,
        )
    except DashboardNotFound as exc:
        print(f"Error: dashboard not found: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        json.dumps({
            "slug": result.slug,
            "originating_user_email": result.originating_user_email,
            "updater_email": result.updater_email,
            "fields_changed": result.fields_changed,
            "directory": f"data/interactive/{result.slug}",
            "conventions_doc_path": "docs/interactive-dashboards.md",
        })
    )


if __name__ == "__main__":
    main()
