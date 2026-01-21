---
name: metabase_query
description: Query Metabase for IAE employment data (project)
---

# Metabase Query Skill

Query the Metabase instances for IAE (Insertion par l'Activite Economique) employment data.

## Documentation

Before querying, read the relevant documentation:
- `knowledge/metabase/` - Tables, schemas, data dictionary
- `knowledge/stats/dashboards/` - Dashboard cards with IDs and SQL
- `knowledge/stats/cards/` - Cards grouped by topic

## Usage

All queries are automatically logged. Use `lib.query`:

```python
from lib.query import execute_metabase_query, CallerType

# Execute a SQL query
result = execute_metabase_query(
    instance='stats',        # or 'datalake', 'dora'
    caller=CallerType.AGENT,
    sql="SELECT COUNT(*) FROM candidatures WHERE etat = 'Candidature acceptee'",
    database_id=2,
)

if result.success:
    print(result.data)  # {"columns": [...], "rows": [...], "row_count": N}
else:
    print(f"Error: {result.error}")

# Execute a saved card/question
result = execute_metabase_query(
    instance='stats',
    caller=CallerType.AGENT,
    card_id=7073,
)
```

### Advanced: Card discovery

Use these patterns to find and explore saved cards:

```python
from lib.query import execute_metabase_query, CallerType

# Get card SQL to understand/modify it
result = execute_metabase_query(
    instance='stats',
    caller=CallerType.AGENT,
    card_id=7073,
)
# Check result.data for the query results

# To search for cards or get metadata, read the knowledge files:
# - knowledge/stats/dashboards/ - Dashboard cards with IDs and SQL
# - knowledge/stats/cards/ - Cards grouped by topic
```

## Available Methods

**Core query methods:**
- `execute_sql(sql)` - Run raw SQL query
- `execute_card(card_id)` - Run a saved question

**Discovery methods:**
- `get_card(card_id)` - Get card metadata
- `get_card_sql(card_id)` - Get SQL for any card (native or compiled)
- `search_cards(query)` - Search cards by name/description
- `list_cards(collection_id)` - List cards in a collection
- `get_dashboard(dashboard_id)` - Get dashboard metadata
- `list_dashboards(collection_id)` - List dashboards in a collection

## Instances

| Instance | URL | Database ID | Purpose |
|----------|-----|-------------|---------|
| stats | stats.inclusion.beta.gouv.fr | 2 | IAE employment statistics |
| datalake | datalake.inclusion.beta.gouv.fr | 2 | Cross-product analytics |
| dora | metabase.dora.inclusion.gouv.fr | 2 | Dora services directory (structures, services, orientations) |
