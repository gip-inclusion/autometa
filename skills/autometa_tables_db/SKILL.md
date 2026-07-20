---
name: autometa_tables_db
description: Query autometa_tables_db — base PostgreSQL centralisant les tables des instances Metabase. Priorité absolue sur Metabase pour toute donnée disponible ici.
---

# autometa_tables_db

Base PostgreSQL contenant les tables exportées depuis les différentes bases de données. À utiliser **en priorité** avant toute requête Metabase.

## Règle de priorité

**Avant toute requête Metabase**, vérifier si les tables nécessaires sont présentes dans `autometa_tables_db` :

1. Interroger `documentation.doc_autometa_tables` pour obtenir la liste et la description des tables disponibles.
2. Si les tables nécessaires sont présentes → requêter `autometa_tables_db` directement en SQL.
3. Si absentes → **ne pas s'arrêter là**. Invoquer le skill `metabase_query` pour rechercher la donnée dans les instances Metabase (`stats`, `datalake`, `dora`). Utiliser `search_cards(query)` pour identifier les cartes pertinentes, puis `execute_card(card_id)` ou `execute_sql(sql)` pour récupérer les données. Ne déclarer une donnée absente qu'après avoir cherché dans autometa_tables_db **et** dans Metabase.

## Règles de sélection des tables

Ordre de préférence, du plus au moins prioritaire :

1. **Tables de référence** (liste ci-dessous) : chercher la donnée ici en premier. Ce sont les tables métier de référence, les plus fiables et les mieux connues. Elles sont réparties entre les schémas autorisés — chercher le nom de table dans l'ensemble de ces schémas plutôt que de présumer d'un schéma précis.
2. **Tables documentées** : si les tables de référence ne couvrent pas le besoin, se limiter aux tables présentes dans `documentation.doc_autometa_tables`.
3. Ne jamais requêter une table ni documentée ni de référence, ni un schéma hors de la liste ci-dessous : les schémas `staging*`, `intermediate*` et `raw*` (sauf `raw_dora`) contiennent des données brutes ou des couches intermédiaires du pipeline, non destinées aux analyses.

### Schémas autorisés

`public`, `monrecap`, `reporting`, `data_inclusion`, `esat`, `seeds`, `raw_dora` (seule exception à l'interdiction de lire les schémas `raw*`), plus `documentation` pour le catalogue.

### Tables de référence

| Domaine | Tables |
|---|---|
| Emplois | `candidats`, `candidatures_echelle_locale`, `fiches_de_poste_par_candidature`, `structures`, `prolongations`, `organisations`, `utilisateurs`, `pass_agréments`, `suspensions_pass`, `suivi_auto_prescription` |
| ASP | `fluxIAE_Structure_v2`, `suivi_realisation_convention_par_structure`, `suivi_realisation_convention_mensuelle`, `suivi_etp_conventionnes_v2`, `fluxIAE_ContratMission_v2`, `fluxIAE_Salarie_v2` |
| Mon Récap | `Contacts`, `Commandes`, `barometre` |
| data·inclusion | `structures_v1`, `services_v1` |
| Datalake | `pdi_base_unique_tous_les_pros` |
| Dora | `structures_structure`, `structures_structuremember`, `services_service`, `services_servicecategory`, `services_service_categories`, `orientations_orientation`, `users_user`, `stats_searchview`, `stats_serviceview`, `stats_mobilisationevent`, `stats_structureinfosview`, `stats_structureview` |

Pour localiser une de ces tables :

```sql
SELECT table_schema, table_name FROM information_schema.tables WHERE table_name = 'candidats'
```

## Documentation des tables

La table `documentation.doc_autometa_tables` contient le catalogue complet :

```python
from lib.query import execute_autometa_tables_query, CallerType

result = execute_autometa_tables_query(
    sql="SELECT table_name, table_description, column_name, column_type, column_description FROM documentation.doc_autometa_tables ORDER BY table_name, column_name",
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
| `public` | Tables métier principales |
| `reporting` | Tables de reporting |
| `monrecap` | Tables Mon Récap |
| `data_inclusion` | Tables data·inclusion |
| `esat` | Tables ESAT |
| `seeds` | Tables de référentiel (seeds dbt) |
| `raw_dora` | Tables Dora brutes — seul schéma `raw*` autorisé |
| `documentation` | Catalogue des tables (`doc_autometa_tables`) |

Tout autre schéma (`staging*`, `intermediate*`, autres `raw*`) est hors périmètre.
