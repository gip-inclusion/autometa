---
name: sync_metabase
description: Sync Metabase cards inventory to markdown files (default) or SQLite database
---

# Metabase Sync Skill

Synchronize Metabase cards from collections to Markdown files for git tracking.

## Usage

```bash
# Full sync with AI categorization (generates markdown)
python -m skills.sync_metabase.scripts.sync_inventory

# Quick sync without AI categorization
python -m skills.sync_metabase.scripts.sync_inventory --skip-categorize

# Also generate SQLite database
python -m skills.sync_metabase.scripts.sync_inventory --sqlite

# SQLite only (no markdown)
python -m skills.sync_metabase.scripts.sync_inventory --sqlite-only

# Sync specific collections
python -m skills.sync_metabase.scripts.sync_inventory --collections 453 452
```

## What it does

1. **Fetches card metadata** from Metabase collections
2. **Extracts SQL queries** (native SQL or compiled from GUI queries)
3. **AI categorization** (optional) - uses Claude to assign topic categories
4. **Writes Markdown files** (default) to `knowledge/stats/`
5. **Writes SQLite database** (optional, with `--sqlite`) to `knowledge/metabase/cards.db`

## Output

### Markdown (default)

- `knowledge/stats/_index.md` - overview with links
- `knowledge/stats/cards/topic-*.md` - cards grouped by topic
- `knowledge/stats/dashboards/dashboard-*.md` - cards per dashboard

### SQLite (optional)

- `knowledge/metabase/cards.db` - full-text searchable database

## Prerequisites

- `METABASE_BASE_URL` and `METABASE_API_KEY` in `.env`
- `ANTHROPIC_API_KEY` in `.env` (for AI categorization)

## Topics

Cards are categorized into these topics:

| Topic | Description |
|-------|-------------|
| file-active | Candidates waiting 30+ days |
| postes-tension | Hard to fill positions |
| candidatures | Application flows |
| demographie | Age/gender breakdowns |
| employeurs | SIAE/employer data |
| prescripteurs | Prescriber data |
| auto-prescription | Auto-prescription metrics |
| controles | Compliance data |
| prolongations | PASS extensions |
| etp-effectifs | Workforce metrics |
| esat | ESAT-specific |
| generalites-iae | General IAE stats |
| autre | Uncategorized |
