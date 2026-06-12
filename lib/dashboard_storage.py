"""Client for the dashboard_storage schema (app database, schema-restricted role)."""

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from .api_signals import emit_api_signal
from .pg import QueryResult


def execute_sql(database_url: str, sql: str, params: dict | None = None, timeout: int = 60) -> QueryResult:
    emit_api_signal(source="dashboard_storage", instance="default", url=database_url, sql=sql)
    engine = create_engine(
        database_url,
        poolclass=NullPool,
        connect_args={"options": f"-c statement_timeout={timeout * 1000}"},
    )
    # Why: begin() commits on success — this client serves writes, unlike its read-only siblings.
    with engine.begin() as conn:
        result = conn.execute(text(sql), params or {})
        if result.returns_rows:
            columns = list(result.keys())
            rows = [list(row) for row in result.fetchall()]
            return QueryResult(columns=columns, rows=rows, row_count=len(rows))
        return QueryResult(columns=[], rows=[], row_count=max(result.rowcount, 0))
