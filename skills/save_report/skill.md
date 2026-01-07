---
name: save_report
description: Save or update a report in the database (project)
---

# Save Report Skill

Create, update, or append reports to the SQLite database.

## Recommended: CLI with File (avoids escaping issues)

**Step 1:** Write report content to a file using the Write tool:

```markdown
# /tmp/report.md
---
date: 2026-01-07
website: emplois
original_query: "User's question"
query_category: "Category name"
---

# Report Title

Report content...
```

**Step 2:** Run the CLI to save to database:

```bash
# Create new report
.venv/bin/python skills/save_report/scripts/save_report.py \
    --file /tmp/report.md \
    --title "Monthly traffic analysis" \
    --website emplois \
    --category "Traffic analysis"

# Update existing report
.venv/bin/python skills/save_report/scripts/save_report.py \
    --file /tmp/report.md \
    --report-id 42

# Append to conversation
.venv/bin/python skills/save_report/scripts/save_report.py \
    --file /tmp/report.md \
    --conversation-id "uuid-here" \
    --title "Follow-up analysis"

# List recent reports
.venv/bin/python skills/save_report/scripts/save_report.py --list
```

## CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--file` | `-f` | Path to markdown file (required) |
| `--title` | `-t` | Report title (required for new/append) |
| `--website` | `-w` | Website: emplois, dora, etc. |
| `--category` | `-c` | Query category |
| `--query` | `-q` | Original user query |
| `--report-id` | `-r` | Report ID to update |
| `--conversation-id` | | Conversation ID to append to |
| `--list` | `-l` | List recent reports |

## Alternative: Python API

For scripts that need programmatic access:

```python
from skills.save_report.scripts.save_report import save_report, update_report, list_reports

result = save_report(
    title="Report title",
    content=content_string,
    website="emplois"
)
```

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
