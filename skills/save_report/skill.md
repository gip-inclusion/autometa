---
name: save_report
description: Save or update a report in the database (project)
---

# Save Report Skill

Create, update, or append reports to the SQLite database.

## Usage

```python
from skills.save_report.scripts.save_report import save_report, update_report, append_report

# Create new report (creates new conversation)
result = save_report(
    title="Monthly traffic analysis",
    content="---\ndate: 2026-01-07\n...",
    website="emplois",
    category="Traffic analysis",
    original_query="What was the traffic in December?"
)
print(f"Created report {result['report_id']} in conversation {result['conversation_id']}")

# Update existing report
result = update_report(
    report_id=42,
    content="Updated report content...",
    title="Updated title"  # optional
)
print(f"Updated report {result['report_id']} to version {result['version']}")

# Append report to existing conversation
result = append_report(
    conversation_id="6ba8debb-937a-4680-a84b-79f21225bc82",
    title="Follow-up analysis",
    content="---\ndate: 2026-01-07\n...",
    website="emplois"
)
print(f"Appended report {result['report_id']}")
```

## Functions

### save_report(title, content, website=None, category=None, original_query=None)

Creates a new conversation and saves the report to it.

Returns: `{"conversation_id": str, "report_id": int, "message_id": int}`

### update_report(report_id, content, title=None, website=None, category=None)

Updates an existing report. Increments version number and updates the linked message content.

Returns: `{"report_id": int, "version": int}`

### append_report(conversation_id, title, content, website=None, category=None, original_query=None)

Appends a new report to an existing conversation.

Returns: `{"conversation_id": str, "report_id": int, "message_id": int}`

## Content Format

Report content should include YAML front-matter:

```yaml
---
date: 2026-01-07
website: emplois
original_query: "User's question"
query_category: "Category name"
indicator_type: [tag1, tag2]
---

# Report Title

Report content in markdown...
```
