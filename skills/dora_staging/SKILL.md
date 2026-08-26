---
name: dora_staging
description: Requêter la base PostgreSQL de Dora staging (préprod) en lecture seule, pour vérifier l'état des données pendant une migration Dora. Base isolée — ses données ne sont jamais mélangées à Metabase, autometa_tables_db ou aux autres sources.
---

# dora_staging

Base PostgreSQL de l'environnement **staging de Dora**. Sert à **tester les migrations de données en cours** : vérifier qu'une migration a produit le résultat attendu, compter les lignes migrées, repérer les valeurs orphelines ou incohérentes avant la mise en production.

## Trois règles non négociables

1. **Lecture seule absolue.** Autometa n'écrit **jamais** sur cette base, sous aucun prétexte, même si l'utilisateur le demande explicitement. C'est PostgreSQL qui l'impose, pas une règle de prompt. Pas d'`INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `CREATE`, `ALTER`, `DROP`, `GRANT`, ni de fonction à effet de bord. Si on vous le demande, refuser et expliquer que la base est en lecture seule côté Autometa ; renvoyer l'utilisateur vers les migrations du dépôt `gip-inclusion/dora`.
2. **Données jamais mélangées.** Ce sont des données de préprod, fausses ou périmées. Ne jamais les joindre, agréger, comparer côte à côte ou consolider avec Metabase, `autometa_tables_db`, `data_inclusion`, Matomo ou RPE. Ne jamais les recopier dans `dashboard_storage`, dans un tableau de bord, dans un rapport d'analyse, dans `knowledge/`, ni dans un dataset publié.
3. **Usage strictement technique.** Toute question métier ou de pilotage relève d'`autometa_tables_db` ou de Metabase.

## Requêter

```python
from lib.query import CallerType, execute_dora_staging_query

result = execute_dora_staging_query(
    sql="SELECT count(*) FROM structures_structure WHERE siret IS NULL",
    caller=CallerType.AGENT,
)

if result.success:
    print(result.data)  # {"columns": [...], "rows": [...], "row_count": N}
else:
    print(result.error)
```

Une seule requête par appel. La connexion est ouverte en `default_transaction_read_only` et le rôle PostgreSQL n'a aucun droit d'écriture : toute tentative d'écriture est refusée par le serveur, et rien n'est jamais commité côté Autometa.

## Explorer le schéma

Le schéma suit les migrations Django de `gip-inclusion/dora` (branche `master`) : les noms de tables sont de la forme `<app>_<modèle>`. Pour l'inventaire courant :

```sql
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name
```

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = '<table>'
ORDER BY ordinal_position
```

Pour vérifier quelles migrations sont appliquées sur l'environnement :

```sql
SELECT app, name, applied FROM django_migrations ORDER BY applied DESC LIMIT 20
```

## Restituer

Annoncer explicitement la source dans la réponse : **« Dora staging (préprod) »**. Ne jamais présenter un chiffre issu de cette base comme un indicateur de production.
