"""Client for the dashboard_storage schema (app database, schema-restricted role)."""

from sqlalchemy import text

from .api_signals import emit_api_signal
from .pg import QueryResult, build_engine


def execute_sql(database_url: str, sql: str, params: dict | None = None, timeout: int = 60) -> QueryResult:
    emit_api_signal(source="dashboard_storage", instance="default", url=database_url, sql=sql)
    engine = build_engine(database_url, timeout)
    # Why: begin() commits on success — this client serves writes, unlike its read-only siblings.
    with engine.begin() as conn:
        result = conn.execute(text(sql), params or {})
        if result.returns_rows:
            columns = list(result.keys())
            rows = [list(row) for row in result.fetchall()]
            return QueryResult(columns=columns, rows=rows, row_count=len(rows))
        return QueryResult(columns=[], rows=[], row_count=max(result.rowcount, 0))
