# Inventaire Metabase

Documentation des cartes et dashboards Metabase pour les données IAE.

## Sources de données

### Markdown (recommandé)

Les cartes sont documentées dans `knowledge/stats/` :
- `_index.md` : vue d'ensemble
- `cards/topic-*.md` : cartes groupées par thème
- `dashboards/dashboard-*.md` : cartes par tableau de bord

Ces fichiers sont versionnés dans git et mis à jour via le skill `sync_metabase`.

### SQLite (optionnel)

Si besoin de requêtes complexes, générer la base SQLite :

```bash
python -m skills.sync_metabase.scripts.sync_inventory --sqlite
```

Crée `knowledge/metabase/cards.db` avec recherche full-text.

## Thèmes

| Thème | Description |
|-------|-------------|
| file-active | Candidats en attente 30+ jours |
| postes-tension | Postes difficiles à pourvoir |
| candidatures | Flux de candidatures |
| demographie | Répartitions âge/genre |
| employeurs | Données SIAE/employeurs |
| prescripteurs | Données prescripteurs |
| auto-prescription | Métriques auto-prescription |
| controles | Données conformité |
| prolongations | Extensions PASS |
| etp-effectifs | Métriques effectifs |
| esat | Données ESAT |
| generalites-iae | Stats générales IAE |

## Synchronisation

```bash
# Sync complet avec catégorisation IA (génère markdown)
python -m skills.sync_metabase.scripts.sync_inventory

# Sans catégorisation IA
python -m skills.sync_metabase.scripts.sync_inventory --skip-categorize

# Générer aussi la base SQLite
python -m skills.sync_metabase.scripts.sync_inventory --sqlite
```

## Schéma SQLite (si utilisé)

```sql
CREATE TABLE cards (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    collection_id INTEGER,
    dashboard_id INTEGER,
    topic TEXT,
    sql_query TEXT,
    tables_referenced TEXT  -- JSON array
);

CREATE TABLE dashboards (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    pilotage_url TEXT,
    collection_id INTEGER
);
```

## Requêtes SQLite

```python
from skills.metabase_query.scripts.cards_db import load_cards_db

db = load_cards_db()
cards = db.search("file active")      # Recherche full-text
cards = db.by_topic("candidatures")   # Par thème
cards = db.by_dashboard(408)          # Par dashboard
card = db.get(7004)                   # Par ID
```
