---
name: publish_dataset
description: Exporter le résultat d'une requête SQL vers S3 sous forme de jeu de données accessible par un job (sqlite/jsonl/csv) avec une URL présignée. À utiliser quand vous composez un run autometa-jobs qui doit analyser des données trop volumineuses pour être embarquées dans le prompt.
---

# Publier un jeu de données

Transforme le résultat d'une requête SQL sur une source PG en un fichier qu'un worker autometa-jobs peut télécharger en HTTPS simple.

Le sandbox du job n'a **aucun accès PG ni aucune connaissance métier d'Autometa** — c'est un conteneur Claude vierge. Tout jeu de données qu'il doit exploiter doit lui être livré sous forme de fichier et récupéré avec `curl`. Cette skill produit ce fichier et une URL de téléchargement à durée limitée.

## Quand l'utiliser

Quand vous (l'agent Autometa) préparez un job qui analyse un jeu de données trop volumineux pour le prompt — par ex. « tous les services Dora ». Vous publiez les données ici, puis vous mettez l'URL renvoyée dans le prompt du job.

## Utilisation

```bash
.venv/bin/python skills/publish_dataset/scripts/publish_dataset.py \
    --slug dora-services \
    --source autometa_tables_db \
    --sql "SELECT id, nom, type, departement FROM dora.services" \
    --format sqlite
```

Affiche du JSON :

```json
{
  "url": "<URL GET présignée, valide ~24h>",
  "format": "sqlite",
  "table": "data",
  "row_count": 1234,
  "columns": ["id", "nom", "type", "departement"],
  "s3_path": "job-inputs/dora-services.sqlite"
}
```

`--source` vaut `autometa_tables_db` (en priorité — vérifiez d'abord `documentation.doc_autometa_tables`) ou `data_inclusion`.

## Plusieurs tables (données relationnelles)

Des données relationnelles (par ex. les services Dora + leurs structures) doivent tenir dans **plusieurs tables JOIN-ables au sein d'un même fichier sqlite**, pas dans une seule table dénormalisée. Passez à `--tables` une map JSON `{nom_table: sql}` :

```bash
.venv/bin/python skills/publish_dataset/scripts/publish_dataset.py \
    --slug dora \
    --source autometa_tables_db \
    --tables '{"structures": "SELECT id, nom, departement FROM dora.structures", "services": "SELECT id, structure_id, nom, type FROM dora.services"}'
```

L'agent du job fait ensuite les JOIN localement : `SELECT s.nom, st.departement FROM services s JOIN structures st ON st.id = s.structure_id`. Les noms de tables doivent respecter `[a-z_][a-z0-9_]*`. Le multi-tables est réservé au format sqlite (jsonl/csv = une table par fichier).

## Formats

- `sqlite` (par défaut) — une table nommée `data`. L'agent du job l'interroge avec le `sqlite3` de la stdlib (SQL complet, rien à installer). Idéal pour des données volumineuses ou relationnelles.
- `jsonl` — un objet JSON par ligne. Idéal pour un raisonnement enregistrement par enregistrement.
- `csv` — en-tête + lignes.

## Remettre le jeu de données à un job

Embarquez l'URL dans le system prompt du job, par ex. :

> Télécharge le jeu de données : `curl -sL '<url>' -o data.sqlite`. C'est une base SQLite avec une table `data` (colonnes : id, nom, type, departement). Interroge-la avec le module `sqlite3` de Python pour répondre à : …

Comme le job n'a aucun contexte Autometa, le prompt que vous écrivez doit aussi porter la **connaissance métier pertinente** (ce que signifient les colonnes, la question métier, comment interpréter les données) — le worker ne peut pas lire la base de connaissance d'Autometa.
