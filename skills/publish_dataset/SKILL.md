---
name: publish_dataset
description: Export a SQL query result to S3 as a job-accessible dataset (sqlite/jsonl/csv) with a presigned URL. Use when composing an autometa-jobs run that must analyze data too large to embed in the job's prompt.
---

# Publish Dataset

Turn a SQL query against a PG source into a file an autometa-jobs worker can download over plain HTTPS.

The job sandbox has **no PG access and none of Autometa's domain knowledge** — it is a blank-slate Claude container. Any dataset it must work on has to be shipped to it as a file and fetched with `curl`. This skill produces that file and a time-boxed download URL.

## When to use

When you (the Autometa agent) are setting up a job that analyzes a dataset too large for the prompt — e.g. "all Dora services". You publish the data here, then put the returned URL in the job's prompt.

## Usage

```bash
.venv/bin/python skills/publish_dataset/scripts/publish_dataset.py \
    --slug dora-services \
    --source autometa_tables_db \
    --sql "SELECT id, nom, type, departement FROM dora.services" \
    --format sqlite
```

Prints JSON:

```json
{
  "url": "<presigned GET URL, valid ~24h>",
  "format": "sqlite",
  "table": "data",
  "row_count": 1234,
  "columns": ["id", "nom", "type", "departement"],
  "s3_path": "job-inputs/dora-services.sqlite"
}
```

`--source` is `autometa_tables_db` (priority — check `documentation.doc_autometa_tables` first) or `data_inclusion`.

## Multiple tables (relational data)

Relational data (e.g. Dora services + their structures) belongs in **several JOIN-able tables in one sqlite file**, not one denormalized table. Pass `--tables` a JSON map of `{table_name: sql}`:

```bash
.venv/bin/python skills/publish_dataset/scripts/publish_dataset.py \
    --slug dora \
    --source autometa_tables_db \
    --tables '{"structures": "SELECT id, nom, departement FROM dora.structures", "services": "SELECT id, structure_id, nom, type FROM dora.services"}'
```

The job agent then JOINs them locally: `SELECT s.nom, st.departement FROM services s JOIN structures st ON st.id = s.structure_id`. Table names must match `[a-z_][a-z0-9_]*`. Multi-table is sqlite-only (jsonl/csv are one-table-per-file).

## Formats

- `sqlite` (default) — one table named `data`. The job agent queries it with stdlib `sqlite3` (full SQL, zero install). Best for large or relational data.
- `jsonl` — one JSON object per line. Best for record-by-record reasoning.
- `csv` — header + rows.

## Handing the dataset to a job

Embed the URL in the job's system prompt, e.g.:

> Download the dataset: `curl -sL '<url>' -o data.sqlite`. It is a SQLite database with one table `data` (columns: id, nom, type, departement). Query it with Python's `sqlite3` to answer: …

Because the job has no Autometa context, the prompt you write must also carry the **relevant domain knowledge** (what the columns mean, the business question, how to interpret the data) — the worker cannot read Autometa's knowledge base.
