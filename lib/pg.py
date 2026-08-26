"""Shared PostgreSQL client — query result type, engine builder, single-statement execution."""

from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from .api_signals import emit_api_signal


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list]
    row_count: int

    def to_markdown(self, max_rows: int = 50) -> str:
        if not self.columns:
            return "(no results)"
        header = "| " + " | ".join(self.columns) + " |"
        sep = "| " + " | ".join("---" for _ in self.columns) + " |"
        lines = [header, sep]
        for row in self.rows[:max_rows]:
            lines.append("| " + " | ".join(str(v) if v is not None else "" for v in row) + " |")
        if self.row_count > max_rows:
            lines.append(f"_({self.row_count - max_rows} lignes supplémentaires)_")
        return "\n".join(lines)


def build_engine(database_url: str, timeout: int, read_only: bool = False):
    """Engine NullPool avec statement_timeout — connexions ponctuelles des clients SQL."""
    options = f"-c statement_timeout={timeout * 1000}"
    if read_only:
        options += " -c default_transaction_read_only=on"
    return create_engine(database_url, poolclass=NullPool, connect_args={"options": options})


def execute_sql(
    database_url: str,
    sql: str,
    source: str,
    instance: str = "default",
    params: dict | None = None,
    write: bool = False,
    timeout: int = 60,
) -> QueryResult:
    """Run one SQL statement on a PostgreSQL source and emit its observability signal."""
    emit_api_signal(source=source, instance=instance, url=database_url, sql=sql)
    engine = build_engine(database_url, timeout, read_only=not write)
    # Why: begin() commits, connect() rolls back on close — a read-only source must never persist anything.
    with engine.begin() if write else engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        if result.returns_rows:
            columns = list(result.keys())
            rows = [list(row) for row in result.fetchall()]
            return QueryResult(columns=columns, rows=rows, row_count=len(rows))
        return QueryResult(columns=[], rows=[], row_count=max(result.rowcount, 0))
