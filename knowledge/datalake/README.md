# Datalake Metabase Instance

**URL:** https://datalake.example.com
**Instance name:** `datalake`

## Usage

```python
from lib.sources import get_metabase

api = get_metabase("datalake")
result = api.execute_sql("SELECT 1", database_id=1)
```

## Databases

| ID | Name | Description |
|----|------|-------------|
| TBD | TBD | TBD |

## Key Tables

TBD - document tables after initial exploration.
