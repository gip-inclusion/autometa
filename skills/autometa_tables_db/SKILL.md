---
name: autometa_tables_db
description: Query autometa_tables_db — base PostgreSQL centralisant les tables des instances Metabase. Priorité absolue sur Metabase pour toute donnée disponible ici.
---

# autometa_tables_db

Base PostgreSQL (via tunnel SSH) contenant les tables exportées depuis les différentes instances Metabase. À utiliser **en priorité** avant toute requête Metabase.

## Règle de priorité

**Avant toute requête Metabase**, vérifier si les tables nécessaires sont présentes dans `autometa_tables_db` :

1. Interroger `documentation.doc_tables_autometa` pour obtenir la liste et la description des tables disponibles.
2. Si les tables nécessaires sont présentes → requêter `autometa_tables_db` directement en SQL.
3. Si absentes → utiliser Metabase normalement.

## Documentation des tables

La table `documentation.doc_tables_autometa` contient le catalogue complet :

```python
from lib.query import execute_autometa_tables_query, CallerType

result = execute_autometa_tables_query(
    sql="SELECT table_name, table_description, column_name, column_type, column_description FROM documentation.doc_tables_autometa ORDER BY table_name, column_name",
    caller=CallerType.AGENT,
)
```

Lire cette table en début de session pour comprendre quelles données sont disponibles et ce que chaque colonne signifie. Elle fait office de dictionnaire de données — s'y référer avant d'écrire des requêtes SQL sur les autres tables.

## Requêter les données

```python
from lib.query import execute_autometa_tables_query, CallerType

result = execute_autometa_tables_query(
    sql="SELECT ... FROM <schema>.<table> WHERE ...",
    caller=CallerType.AGENT,
)

if result.success:
    print(result.data)  # {"columns": [...], "rows": [...], "row_count": N}
else:
    print(result.error)
```

## Schémas disponibles

| Schéma | Contenu |
|---|---|
| `les_emplois` | Tables issues de l'instance Metabase Emplois |
| `dora` | Tables issues de l'instance Metabase Dora |
| `data_inclusion` | Tables issues de l'instance Metabase data·inclusion |
| `monrecap` | Tables issues de l'instance Metabase Mon Récap |
| `asp` | Tables issues de l'instance Metabase ASP |
| `datalake` | Tables issues de l'instance Metabase Datalake |
| `documentation` | Catalogue des tables (`doc_tables_autometa`) |

## Performance

Chaque requête ouvre un tunnel SSH (~200ms overhead). Combiner les SELECT avec UNION ALL ou des CTEs plutôt que de faire plusieurs appels séparés.
