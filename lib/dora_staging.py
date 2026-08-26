"""Client strictement en lecture pour la base Dora staging (validation des migrations de données)."""

from sqlalchemy import text

from .api_signals import emit_api_signal
from .pg import QueryResult, build_engine

READ_ONLY_PREFIXES = ("select", "with", "table", "values", "explain", "show")


class ReadOnlyViolation(Exception):
    """Requête refusée : Autometa n'écrit jamais sur Dora staging."""


def assert_read_only(sql: str) -> None:
    statement = sql.strip().rstrip(";")
    if ";" in statement:
        raise ReadOnlyViolation("Une seule requête par appel : le « ; » intermédiaire est refusé.")
    if not statement.lower().startswith(READ_ONLY_PREFIXES):
        raise ReadOnlyViolation(
            f"Dora staging est en lecture seule : seules les requêtes {'/'.join(READ_ONLY_PREFIXES).upper()} "
            "sont autorisées."
        )


def execute_sql(database_url: str, sql: str, timeout: int = 60) -> QueryResult:
    assert_read_only(sql)
    emit_api_signal(source="dora_staging", instance="staging", url=database_url, sql=sql)
    engine = build_engine(database_url, timeout, read_only=True)
    # Why: connect() sans commit + default_transaction_read_only côté serveur — double verrou anti-écriture.
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = [list(row) for row in result.fetchall()]
        return QueryResult(columns=columns, rows=rows, row_count=len(rows))
