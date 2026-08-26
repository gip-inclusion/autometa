"""Client strictement en lecture pour la base Dora staging (validation des migrations de données)."""

from sqlalchemy import text

from .api_signals import emit_api_signal
from .pg import QueryResult, build_engine


def execute_sql(database_url: str, sql: str, timeout: int = 60) -> QueryResult:
    emit_api_signal(source="dora_staging", instance="staging", url=database_url, sql=sql)
    engine = build_engine(database_url, timeout, read_only=True)
    # Why: connect() sans commit + default_transaction_read_only côté serveur — l'écriture est refusée par PostgreSQL.
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = [list(row) for row in result.fetchall()]
        return QueryResult(columns=columns, rows=rows, row_count=len(rows))
