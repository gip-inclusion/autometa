---
name: appli_monrecap_db
description: Requêter la base PostgreSQL de l'application Mon Récap (lecture et écriture), uniquement sur demande explicite de l'utilisateur. Jamais utilisée pour de l'analyse de données.
---

# appli_monrecap_db

Base PostgreSQL de l'application **Mon Récap** (mon-recap.inclusion.beta.gouv.fr, cf. `knowledge/sites/mon-recap.md`). Contrairement à Matomo (comportement des visiteurs) ou `autometa_tables_db` (analyse métier), cette base donne un accès direct aux données de l'application elle-même.

## Deux règles non négociables

1. **Sur demande explicite uniquement.** N'interroger ou écrire sur cette base que lorsque l'utilisateur le demande précisément dans son message courant — jamais de manière autonome, jamais en complément d'une autre tâche, jamais depuis un job planifié ou un cron.
2. **Jamais pour l'analyse de données.** Cette base ne sert pas à produire des statistiques, des tableaux de bord ou des rapports. Ne jamais y agréger, joindre ou comparer des données avec Metabase, `autometa_tables_db`, Matomo, data·inclusion ou RPE. Ne jamais recopier son contenu dans `dashboard_storage`, un tableau de bord, un rapport, `knowledge/`, ni un dataset publié. Pour une question d'analyse ou de pilotage sur Mon Récap, se tourner vers `autometa_tables_db` ou Metabase.

## Requêter

```python
from lib.query import CallerType, execute_appli_monrecap_query

result = execute_appli_monrecap_query(
    sql="SELECT id, email FROM users WHERE email = :email",
    caller=CallerType.AGENT,
    params={"email": "exemple@test.fr"},
)

if result.success:
    print(result.data)  # {"columns": [...], "rows": [...], "row_count": N}
else:
    print(result.error)
```

Lecture et écriture sont toutes deux possibles (`INSERT`, `UPDATE`, `DELETE` compris) : une seule requête par appel, exécutée dans sa propre transaction commitée. Avant toute écriture, confirmer avec l'utilisateur la requête exacte qui va être exécutée.

## Explorer le schéma

```sql
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name
```

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = '<table>'
ORDER BY ordinal_position
```

## Restituer

Annoncer explicitement la source dans la réponse : **« base applicative Mon Récap »**.
