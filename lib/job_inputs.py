"""Publish a query result to S3 as a job-accessible dataset (sqlite/jsonl/csv) with a presigned URL."""

import csv
import io
import json
import re
import sqlite3
import tempfile
from pathlib import Path

from lib.query import CallerType, execute_autometa_tables_query, execute_data_inclusion_query
from web import s3

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
# Presigned URL must outlive the job's startup fetch; jobs run up to 24h and the agent downloads immediately.
DEFAULT_EXPIRES = 86400


def _coerce(value):
    if value is None or isinstance(value, (int, float, str)):
        return value
    return str(value)


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _to_sqlite(table: str, columns: list[str], rows: list[list]) -> bytes:
    # Why: SQL can't bind identifiers (table/column names), only values — so identifiers are
    # quote-escaped and concatenated while row values go through ? placeholders.
    cols = ", ".join(_quote_ident(c) for c in columns)
    marks = ", ".join("?" for _ in columns)
    create_sql = "CREATE TABLE " + _quote_ident(table) + " (" + cols + ")"
    insert_sql = "INSERT INTO " + _quote_ident(table) + " VALUES (" + marks + ")"
    with tempfile.NamedTemporaryFile(suffix=".sqlite") as tmp:
        conn = sqlite3.connect(tmp.name)
        try:
            conn.execute(create_sql)
            conn.executemany(insert_sql, rows)
            conn.commit()
        finally:
            conn.close()
        return Path(tmp.name).read_bytes()


def _to_jsonl(columns: list[str], rows: list[list]) -> bytes:
    lines = (json.dumps(dict(zip(columns, row)), ensure_ascii=False) for row in rows)
    return ("\n".join(lines) + "\n").encode()


def _to_csv(columns: list[str], rows: list[list]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    writer.writerows(rows)
    return buf.getvalue().encode()


def publish_dataset(
    slug: str,
    columns: list[str],
    rows: list[list],
    fmt: str = "sqlite",
    table: str = "data",
    expires_in: int = DEFAULT_EXPIRES,
) -> dict:
    if not SLUG_RE.match(slug):
        raise ValueError(f"invalid slug: {slug!r} (use [a-z0-9_-])")
    rows = [[_coerce(v) for v in row] for row in rows]
    if fmt == "sqlite":
        content, ctype = _to_sqlite(table, columns, rows), "application/x-sqlite3"
    elif fmt == "jsonl":
        content, ctype = _to_jsonl(columns, rows), "application/x-ndjson"
    elif fmt == "csv":
        content, ctype = _to_csv(columns, rows), "text/csv"
    else:
        raise ValueError(f"unsupported format: {fmt!r} (use sqlite, jsonl, or csv)")

    path = f"{slug}.{fmt}"
    if not s3.job_inputs.upload(path, content, content_type=ctype):
        raise RuntimeError(f"S3 upload failed for {path}")
    url = s3.job_inputs.get_url(path, expires_in=expires_in)
    if not url:
        raise RuntimeError(f"could not presign URL for {path}")
    return {
        "url": url,
        "format": fmt,
        "table": table if fmt == "sqlite" else None,
        "row_count": len(rows),
        "columns": columns,
        "s3_path": f"job-inputs/{path}",
    }


def publish_query(
    slug: str,
    source: str,
    sql: str,
    fmt: str = "sqlite",
    timeout: int = 60,
    expires_in: int = DEFAULT_EXPIRES,
) -> dict:
    if source == "autometa_tables_db":
        result = execute_autometa_tables_query(sql=sql, caller=CallerType.AGENT, timeout=timeout)
    elif source == "data_inclusion":
        result = execute_data_inclusion_query(sql=sql, caller=CallerType.AGENT, timeout=timeout)
    else:
        raise ValueError(f"unsupported source: {source!r} (use autometa_tables_db or data_inclusion)")
    if not result.success:
        raise RuntimeError(f"query failed: {result.error}")
    return publish_dataset(slug, result.data["columns"], result.data["rows"], fmt=fmt, expires_in=expires_in)
