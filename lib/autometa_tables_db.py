"""Client for autometa_tables_db (direct PostgreSQL connection — same Scalingo region)."""

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from .api_signals import emit_api_signal
from .pg import QueryResult


def execute_sql(database_url: str, sql: str, timeout: int = 60) -> QueryResult:
    emit_api_signal(source="autometa_tables_db", instance="default", url=database_url, sql=sql)
    engine = create_engine(
        database_url,
        poolclass=NullPool,
        connect_args={"options": f"-c statement_timeout={timeout * 1000}"},
    )
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = [list(row) for row in result.fetchall()]
        return QueryResult(columns=columns, rows=rows, row_count=len(rows))
