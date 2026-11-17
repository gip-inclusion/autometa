---
name: save_report
description: Save or update a report in the database (project)
---

# Save Report Skill

> Avant d'écrire : relire chaque chiffre contre les sorties d'outil, et poser la question si la cible est ambiguë (`AGENT.md`, « Chiffres et affirmations »).

Create or update reports in the PostgreSQL database.

## Recommended: CLI with File (avoids escaping issues)

**Step 1:** Write report content to a file using the Write tool, in the conversation folder (its full path is given at the end of the system prompt):

```markdown
# /tmp/$AUTOMETA_CONVERSATION_ID/report.md
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
# Create new report (ALWAYS include --tags)
python skills/save_report/scripts/save_report.py \
    --file /tmp/$AUTOMETA_CONVERSATION_ID/report.md \
    --title "Monthly traffic analysis" \
    --website emplois \
    --category "Traffic analysis" \
    --tags "explo,emplois,trafic"

# Update existing report
python skills/save_report/scripts/save_report.py \
    --file /tmp/$AUTOMETA_CONVERSATION_ID/report.md \
    --report-id 42

# List recent reports
python skills/save_report/scripts/save_report.py --list

# Read a report (metadata, then content)
python skills/save_report/scripts/save_report.py --show 42

# Find reports whose title or content contains every word
python skills/save_report/scripts/save_report.py --search "orientations prescripteurs"
```

Un nouveau rapport est enregistré au nom de l'utilisateur et rattaché à la conversation en cours, d'après l'environnement : jamais à une conversation citée par lien.

## CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--file` | `-f` | Path to markdown file (required) |
| `--title` | `-t` | Report title (required for new reports) |
| `--website` | `-w` | Website: emplois, dora, etc. |
| `--category` | `-c` | Query category |
| `--query` | `-q` | Original user query |
| `--tags` | | **REQUIRED** Comma-separated tags, all from the synced vocabulary (see § Tags) |
| `--report-id` | `-r` | Report ID to update — only a report of the current user (check with `--show`) |
| `--list` | `-l` | List recent reports |
| `--show` | | Report ID to read (read-only) |
| `--search` | | Words to find in report titles and contents (read-only) |

## Tags (REQUIRED)

Les tags viennent d'un **vocabulaire fermé**, synchronisé depuis Notion et organisé en facettes (`usage`, `feature`, `audience`, `theme`, `mesure`, `source`, `territoire`). Un terme absent du vocabulaire actif est refusé et l'opération échoue : il n'y a plus de création de tag à la volée. Lister les termes valides et le nombre attendu par facette avant de choisir :

```bash
python skills/list_tags.py
```

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
