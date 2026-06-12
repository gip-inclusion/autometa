"""Client for autometa_tables_db (direct PostgreSQL connection — same Scalingo region)."""

from sqlalchemy import text

from .api_signals import emit_api_signal
from .pg import QueryResult, build_engine


def execute_sql(database_url: str, sql: str, timeout: int = 60) -> QueryResult:
    emit_api_signal(source="autometa_tables_db", instance="default", url=database_url, sql=sql)
    engine = build_engine(database_url, timeout)
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = [list(row) for row in result.fetchall()]
        return QueryResult(columns=columns, rows=rows, row_count=len(rows))
