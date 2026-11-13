"""Save report skill - create, update, show or search reports in the database."""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from web import config  # noqa: E402
from web.database import ConversationStore  # noqa: E402


def save_report(
    title: str,
    content: str,
    website: str = None,
    category: str = None,
    original_query: str = None,
    tags: list[str] = None,
) -> dict:
    """Crée le rapport au nom de l'utilisateur de la conversation en cours, et l'y rattache."""
    store = ConversationStore()
    conversation_id = config.agent_conversation_id()

    report = store.create_report(
        title=title,
        content=content,
        website=website,
        category=category,
        original_query=original_query,
        source_conversation_id=conversation_id,
        user_id=config.agent_user_email(),
    )

    if tags:
        store.set_report_tags(report.id, tags, update_timestamp=False)

    if conversation_id:
        store.add_message(conversation_id, "report", json.dumps({"report_id": report.id, "title": report.title}))

    return {
        "report_id": report.id,
        "source_conversation_id": conversation_id,
    }


def update_report(
    report_id: int,
    content: str,
    title: str = None,
    website: str = None,
    category: str = None,
) -> dict:
    store = ConversationStore()

    # Get the report to verify it exists
    report = store.get_report(report_id)
    if not report:
        raise ValueError(f"Report {report_id} not found")

    # Update report content and metadata
    updates = {"content": content}
    if title:
        updates["title"] = title
    if website:
        updates["website"] = website
    if category:
        updates["category"] = category

    store.update_report(report_id, **updates)

    # Get updated version
    updated_report = store.get_report(report_id)

    return {
        "report_id": report_id,
        "version": updated_report.version,
    }


def list_reports(website: str = None, category: str = None, limit: int = 20) -> list:
    store = ConversationStore()
    reports = store.list_reports(website=website, category=category, limit=limit)

    return [
        {
            "id": r.id,
            "title": r.title,
            "website": r.website,
            "category": r.category,
            "version": r.version,
            "source_conversation_id": r.source_conversation_id,
        }
        for r in reports
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Save or update reports in the database")
    parser.add_argument("--file", "-f", help="Path to markdown file containing report content")
    parser.add_argument("--title", "-t", help="Report title")
    parser.add_argument("--website", "-w", help="Website (emplois, dora, etc.)")
    parser.add_argument("--category", "-c", help="Query category")
    parser.add_argument("--query", "-q", help="Original user query")
    parser.add_argument(
        "--tags", help="Comma-separated tags, all from the synced vocabulary (e.g. 'explo,emplois,trafic')"
    )
    parser.add_argument("--report-id", "-r", type=int, help="Report ID to update (for updates)")
    parser.add_argument("--list", "-l", action="store_true", help="List recent reports")
    parser.add_argument("--search", help="List reports whose title or content contains every word")
    parser.add_argument("--show", type=int, metavar="REPORT_ID", help="Print a report's metadata and content")

    args = parser.parse_args()

    if args.show:
        report = ConversationStore().get_report(args.show)
        if not report:
            print(f"Error: report {args.show} not found", file=sys.stderr)
            sys.exit(1)
        conversation = f"/explorations/{report.source_conversation_id}" if report.source_conversation_id else "N/A"
        print(
            f"[{report.id}] {report.title} (v{report.version}) - {report.website or 'N/A'} - "
            f"{report.user_id or 'N/A'} - {conversation} - {report.updated_at:%Y-%m-%d}\n"
        )
        print(report.content)
        sys.exit(0)

    if args.list or args.search:
        store = ConversationStore()
        reports = store.search_reports(args.search) if args.search else store.list_reports(limit=10)
        for r in reports:
            print(f"  [{r.id}] {r.title} (v{r.version}) - {r.website or 'N/A'} - {r.updated_at:%Y-%m-%d}")
        sys.exit(0)

    if not args.file:
        parser.error("--file is required for save/update operations")

    # Read content from file
    content_path = Path(args.file)
    if not content_path.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    content = content_path.read_text()

    # Parse tags
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else None

    if args.report_id:
        # Update existing report
        result = update_report(
            report_id=args.report_id,
            content=content,
            title=args.title,
            website=args.website,
            category=args.category,
        )
        print(f"Updated report {result['report_id']} to version {result['version']}")

    else:
        if not args.title:
            parser.error("--title is required for new reports")
        result = save_report(
            title=args.title,
            content=content,
            website=args.website,
            category=args.category,
            original_query=args.query,
            tags=tags,
        )
        print(f"Created report {result['report_id']}")
