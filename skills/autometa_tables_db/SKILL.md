---
name: autometa_tables_db
description: Query autometa_tables_db, la base PostgreSQL centrale qui regroupe les tables des instances Metabase (Emplois, ASP, Mon Récap, data·inclusion, Dora, RDV-Insertion…).
---

# autometa_tables_db

Base PostgreSQL contenant les tables exportées depuis les différentes bases de données.

## Ordre des sources

L'ordre entre cette base et Metabase est fixé par `AGENT.md` (section « Sources de données ») ; ce skill ne le recopie pas. Dans cette base, commencer par le catalogue `documentation.doc_autometa_tables` (voir plus bas), puis appliquer les règles de sélection des tables.

## Règles de sélection des tables

Ordre de préférence, du plus au moins prioritaire :

1. **Tables de référence** (liste ci-dessous) : chercher la donnée ici en premier. Ce sont les tables métier de référence, les plus fiables et les mieux connues. Elles sont réparties entre les schémas autorisés — chercher le nom de table dans l'ensemble de ces schémas plutôt que de présumer d'un schéma précis.
2. **Tables documentées** : si les tables de référence ne couvrent pas le besoin, se limiter aux tables présentes dans `documentation.doc_autometa_tables`.
3. Ne jamais requêter une table ni documentée ni de référence, ni un schéma hors de la liste ci-dessous : les schémas `staging*` et `intermediate*` sont des couches intermédiaires du pipeline, non destinées aux analyses.

Ordre des schémas : chercher d'abord dans `reporting`, puis dans `public`, et seulement ensuite dans les schémas `raw*`. Les schémas `raw*` (hors `raw_dora` et `raw_rdvi`) contiennent les données brutes : avant d'y requêter, demander à l'utilisateur s'il veut vraiment aller chercher dans les données brutes, et attendre son accord.

Pour Dora spécifiquement : chercher d'abord dans `fct_dora__imer` et `fct_dora__orientations` (tables de référence) avant de se rabattre sur `raw_dora`.

### Schémas autorisés

`reporting`, `public`, `monrecap`, `data_inclusion`, `esat`, `seeds`, `raw_dora`, `raw_rdvi`, plus `documentation` pour le catalogue. Les autres schémas `raw*` ne se lisent qu'après accord explicite de l'utilisateur.

### Tables de référence

| Domaine | Tables |
|---|---|
| Emplois | `candidats`, `candidatures_echelle_locale`, `fiches_de_poste_par_candidature`, `structures`, `prolongations`, `organisations`, `utilisateurs`, `pass_agréments`, `suspensions_pass`, `suivi_auto_prescription` |
| ASP | `fluxIAE_Structure_v2`, `suivi_realisation_convention_par_structure`, `suivi_realisation_convention_mensuelle`, `suivi_etp_conventionnes_v2`, `fluxIAE_ContratMission_v2`, `fluxIAE_Salarie_v2` |
| Mon Récap | `Contacts`, `Commandes`, `barometre` |
| data·inclusion | `structures_v1`, `services_v1` |
| Datalake | `pdi_base_unique_tous_les_pros` |
| Dora | `fct_dora__imer`, `fct_dora__orientations` |

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

## Pièges

Les colonnes de date des tables issues des Emplois sont du **texte** ISO, pas des dates. Écrire
`colonne::date >= x` écarte l'index et double le coût de la requête : comparer comme du
texte, et passer par `TO_CHAR` quand le terme de droite n'est pas un littéral.

## Schémas disponibles

Cette liste est indicative — la source de vérité est `documentation.doc_autometa_tables`,
à interroger à l'exécution.

| Schéma | Contenu |
|---|---|
| `reporting` | Tables de reporting |
| `public` | Tables métier principales |
| `monrecap` | Tables Mon Récap |
| `data_inclusion` | Tables data·inclusion |
| `esat` | Tables ESAT |
| `seeds` | Tables de référentiel (seeds dbt) |
| `raw_dora` | Tables Dora brutes — lisible sans demander |
| `raw_rdvi` | Copie quotidienne du schéma `rdvi` (RDV-Insertion) de la base ETL qui alimente le Metabase rdvi — lisible sans demander. Lire `knowledge/rdvi/README.md` avant de requêter |
| autres `raw*` | Données brutes — uniquement après accord de l'utilisateur |
| `documentation` | Catalogue des tables (`doc_autometa_tables`) |

Les schémas `staging*` et `intermediate*` sont hors périmètre.
