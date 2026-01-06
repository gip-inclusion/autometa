# Metabase Integration Design

**Date:** 2026-01-03
**Status:** Approved

Merge cyberyayou Metabase exploration tools into Matometa, creating Python skills for querying and syncing Metabase data.

---

## 1. Environment & Project Structure

### New .env variables

```
METABASE_BASE_URL=https://stats.inclusion.beta.gouv.fr
METABASE_API_KEY=mb_...
METABASE_DATABASE_ID=2
```

### New directories/files

```
skills/
├── metabase-query/           # Query skill
│   ├── skill.md
│   └── scripts/
│       ├── __init__.py
│       └── metabase.py       # Python client
│
└── metabase-sync/            # Scraping/sync skill
    ├── skill.md
    └── scripts/
        ├── __init__.py
        └── sync_inventory.py

knowledge/
└── metabase/
    ├── README.md             # Index: schema, categories, how to query
    └── cards.db              # SQLite: full inventory

tests/
├── test_metabase_client.py   # Unit tests for client
└── test_metabase_answers.py  # Answer verification scaffold
```

---

## 2. Metabase Python Client

### Core class: `MetabaseAPI`

```python
class MetabaseAPI:
    def __init__(self, url=None, api_key=None, database_id=None):
        # Loads from .env if not provided

    # --- Core methods ---
    def execute_sql(self, sql: str) -> QueryResult
        # POST /api/dataset with native query

    def execute_card(self, card_id: int) -> QueryResult
        # POST /api/card/{id}/query

    def get_card(self, card_id: int) -> dict
        # GET /api/card/{id}

    # --- Discovery methods ---
    def list_cards(self, collection_id: int) -> list[dict]
        # GET /api/collection/{id}/items

    def search_cards(self, query: str) -> list[dict]
        # GET /api/search?q={query}&models=card

    def get_card_sql(self, card_id: int) -> str
        # Returns native SQL or compiled SQL from GUI query
```

### QueryResult dataclass

```python
@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]
    row_count: int

    def to_markdown(self) -> str  # Table format
    def to_dicts(self) -> list[dict]  # Row dicts
```

Authentication uses `X-API-KEY` header (no session management needed).

---

## 3. SQLite Storage & Markdown Index

### SQLite schema (`knowledge/metabase/cards.db`)

```sql
CREATE TABLE cards (
    id INTEGER PRIMARY KEY,      -- Metabase card ID
    name TEXT NOT NULL,
    description TEXT,
    collection_id INTEGER,
    topic TEXT,                   -- AI-assigned category
    sql_query TEXT,               -- Full SQL (native or compiled)
    tables_referenced TEXT,       -- JSON array of table names
    created_at TEXT,
    updated_at TEXT               -- Last sync time
);

CREATE INDEX idx_cards_topic ON cards(topic);
CREATE INDEX idx_cards_collection ON cards(collection_id);

-- Full-text search on name, description, SQL
CREATE VIRTUAL TABLE cards_fts USING fts5(
    name, description, sql_query, content=cards, content_rowid=id
);
```

### Markdown index (`knowledge/metabase/README.md`)

```markdown
# Metabase Cards Inventory

Database: `knowledge/metabase/cards.db`
Last synced: 2026-01-03
Total cards: ~335

## Database Schema

\`\`\`sql
CREATE TABLE cards (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    collection_id INTEGER,
    topic TEXT,
    sql_query TEXT,
    tables_referenced TEXT,  -- JSON array
    created_at TEXT,
    updated_at TEXT
);

CREATE VIRTUAL TABLE cards_fts USING fts5(
    name, description, sql_query
);
\`\`\`

## Topics

| Topic | Count | Description |
|-------|-------|-------------|
| candidatures | 45 | Application flows and states |
| file-active | 23 | 30+ day waiting candidates |
| demographie | 18 | Age, gender breakdowns |
...

## Querying the database

\`\`\`python
from skills.metabase_query.scripts.metabase import load_cards_db
db = load_cards_db()
cards = db.search("file active")  # FTS search
cards = db.by_topic("candidatures")  # Filter by topic
\`\`\`

## Key tables referenced

- candidatures_recues_par_fiche_de_poste (89 cards)
- explo_carto.candidatures_et_fiches_de_poste (52 cards)
- fiches_de_poste (34 cards)
```

---

## 4. Sync Skill

### Purpose

Simplified version of `build_inventory.py`:
- Fetches cards from collections 452, 453 (configurable)
- Extracts SQL (native or compiled via query execution)
- Categorizes with Claude (batched, using existing topic taxonomy)
- Writes to SQLite + regenerates README.md

### Usage

```bash
python -m skills.metabase_sync.scripts.sync_inventory
python -m skills.metabase_sync.scripts.sync_inventory --skip-categorize
```

---

## 5. Test Suites

### Test suite 1: `tests/test_metabase_client.py`

```python
def test_connection():
    # Verify API key works

def test_execute_sql():
    # Simple query: SELECT 1 as test

def test_execute_card():
    # Run a known card ID, check structure

def test_get_card():
    # Fetch card metadata

def test_list_cards():
    # List cards in collection 452

def test_search_cards():
    # Search for "candidature"
```

### Test suite 2: `tests/test_metabase_answers.py`

Answer verification tests the whole agent flow:

```python
@dataclass
class ExpectedAnswer:
    question: str              # Natural language prompt
    expected_range: tuple[int, int]  # For numeric answers

KNOWN_ANSWERS = [
    ExpectedAnswer(
        "Combien de candidats sont dans la file active ?",
        (90000, 110000)
    ),
    ExpectedAnswer(
        "Combien de postes en tension sont ouverts ?",
        (2500, 3500)
    ),
]

def test_known_answers():
    for case in KNOWN_ANSWERS:
        # Agent uses tools to find answer
        # Assert result in expected range
```

---

## 6. Dashboard Mapping (Stretch Goal)

### Additional schema

```sql
CREATE TABLE dashboards (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,            -- From dashboard's first tab/header
    pilotage_url TEXT,
    collection_id INTEGER
);

CREATE TABLE dashboard_cards (
    dashboard_id INTEGER,
    card_id INTEGER,
    position INTEGER,
    tab_name TEXT,               -- Which tab the card is on
    FOREIGN KEY (dashboard_id) REFERENCES dashboards(id),
    FOREIGN KEY (card_id) REFERENCES cards(id)
);
```

### Sync process

1. Fetch dashboard metadata via `GET /api/dashboard/{id}`
2. Extract description from first tab's text cards or dashboard description field
3. Store tab structure so we know which cards are grouped together

### README addition

```markdown
## Dashboards

### File active IAE
URL: pilotage.inclusion.beta.gouv.fr/tableaux-de-bord/file-active
Description: Suivi des candidats en recherche active depuis plus de 30 jours
sans avoir reçu d'acceptation. Permet d'identifier les blocages dans le
parcours d'insertion.

Cards: 4413 (count), 4493 (postes ouverts), 4803 (genre), 4804 (âge)...
```

---

## Implementation Order

1. Add .env variables
2. Create `MetabaseAPI` client + tests
3. Create SQLite schema + `load_cards_db()` helper
4. Create sync skill (populate DB)
5. Generate README.md index
6. Create answer verification test scaffold
7. (Stretch) Dashboard mapping
