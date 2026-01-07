"""Save report skill - create, update, or append reports to the database."""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from web.database import ConversationStore, get_db


def save_report(
    title: str,
    content: str,
    website: str = None,
    category: str = None,
    original_query: str = None,
) -> dict:
    """
    Create a new conversation and save a report to it.

    Args:
        title: Report title (also used as conversation title)
        content: Report content (markdown with YAML front-matter)
        website: Website name (emplois, dora, etc.)
        category: Query category
        original_query: Original user question

    Returns:
        {"conversation_id": str, "report_id": int, "message_id": int}
    """
    store = ConversationStore()

    # Create conversation
    conv = store.create_conversation()
    store.update_conversation(conv.id, title=title)

    # Add user message if we have the original query
    if original_query:
        store.add_message(conv.id, "user", original_query)

    # Add report as assistant message
    msg = store.add_message(conv.id, "assistant", content)

    # Create report record
    report = store.create_report(
        conv_id=conv.id,
        message_id=msg.id,
        title=title,
        website=website,
        category=category,
        original_query=original_query,
    )

    return {
        "conversation_id": conv.id,
        "report_id": report.id,
        "message_id": msg.id,
    }


def update_report(
    report_id: int,
    content: str,
    title: str = None,
    website: str = None,
    category: str = None,
) -> dict:
    """
    Update an existing report's content and metadata.

    Args:
        report_id: ID of the report to update
        content: New report content
        title: New title (optional)
        website: New website (optional)
        category: New category (optional)

    Returns:
        {"report_id": int, "version": int}
    """
    store = ConversationStore()

    # Get the report to find message_id
    report = store.get_report(report_id)
    if not report:
        raise ValueError(f"Report {report_id} not found")

    # Update the message content
    with get_db() as conn:
        conn.execute(
            "UPDATE messages SET content = ? WHERE id = ?",
            (content, report.message_id)
        )

    # Update report metadata
    updates = {}
    if title:
        updates["title"] = title
    if website:
        updates["website"] = website
    if category:
        updates["category"] = category

    if updates:
        store.update_report(report_id, **updates)
    else:
        # Just bump the version even if no metadata changed
        with get_db() as conn:
            conn.execute(
                "UPDATE reports SET version = version + 1, updated_at = datetime('now') WHERE id = ?",
                (report_id,)
            )

    # Get updated version
    updated_report = store.get_report(report_id)

    return {
        "report_id": report_id,
        "version": updated_report.version,
    }


def append_report(
    conversation_id: str,
    title: str,
    content: str,
    website: str = None,
    category: str = None,
    original_query: str = None,
) -> dict:
    """
    Append a new report to an existing conversation.

    Args:
        conversation_id: ID of the conversation to append to
        title: Report title
        content: Report content
        website: Website name
        category: Query category
        original_query: Original user question

    Returns:
        {"conversation_id": str, "report_id": int, "message_id": int}
    """
    store = ConversationStore()

    # Verify conversation exists
    conv = store.get_conversation(conversation_id, include_messages=False)
    if not conv:
        raise ValueError(f"Conversation {conversation_id} not found")

    # Add report as assistant message
    msg = store.add_message(conversation_id, "assistant", content)

    # Create report record
    report = store.create_report(
        conv_id=conversation_id,
        message_id=msg.id,
        title=title,
        website=website,
        category=category,
        original_query=original_query,
    )

    return {
        "conversation_id": conversation_id,
        "report_id": report.id,
        "message_id": msg.id,
    }


def list_reports(website: str = None, category: str = None, limit: int = 20) -> list:
    """
    List existing reports.

    Args:
        website: Filter by website
        category: Filter by category
        limit: Max reports to return

    Returns:
        List of report dicts with id, title, website, category, version
    """
    store = ConversationStore()
    reports = store.list_reports(website=website, category=category, limit=limit)

    return [
        {
            "id": r.id,
            "title": r.title,
            "website": r.website,
            "category": r.category,
            "version": r.version,
            "conversation_id": r.conversation_id,
        }
        for r in reports
    ]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Save or update reports in the database")
    parser.add_argument("--file", "-f", help="Path to markdown file containing report content")
    parser.add_argument("--title", "-t", help="Report title")
    parser.add_argument("--website", "-w", help="Website (emplois, dora, etc.)")
    parser.add_argument("--category", "-c", help="Query category")
    parser.add_argument("--query", "-q", help="Original user query")
    parser.add_argument("--report-id", "-r", type=int, help="Report ID to update (for updates)")
    parser.add_argument("--conversation-id", help="Conversation ID to append to")
    parser.add_argument("--list", "-l", action="store_true", help="List recent reports")

    args = parser.parse_args()

    if args.list:
        reports = list_reports(limit=10)
        print("Recent reports:")
        for r in reports:
            print(f"  [{r['id']}] {r['title']} (v{r['version']}) - {r['website'] or 'N/A'}")
        sys.exit(0)

    if not args.file:
        parser.error("--file is required for save/update operations")

    # Read content from file
    content_path = Path(args.file)
    if not content_path.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    content = content_path.read_text()

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

    elif args.conversation_id:
        # Append to existing conversation
        if not args.title:
            parser.error("--title is required when appending to conversation")
        result = append_report(
            conversation_id=args.conversation_id,
            title=args.title,
            content=content,
            website=args.website,
            category=args.category,
            original_query=args.query,
        )
        print(f"Appended report {result['report_id']} to conversation {result['conversation_id']}")

    else:
        # Create new report
        if not args.title:
            parser.error("--title is required for new reports")
        result = save_report(
            title=args.title,
            content=content,
            website=args.website,
            category=args.category,
            original_query=args.query,
        )
        print(f"Created report {result['report_id']} in conversation {result['conversation_id']}")
