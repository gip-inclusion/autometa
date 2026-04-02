"""Client for the data·inclusion datawarehouse (PostgreSQL via SSH tunnel)."""

import io
from dataclasses import dataclass
from urllib.parse import urlparse

import paramiko
import psycopg2

from .api_signals import emit_api_signal

# sshtunnel 0.4.0 references paramiko.DSSKey which was removed in paramiko 4.0
if not hasattr(paramiko, "DSSKey"):
    paramiko.DSSKey = None

from sshtunnel import SSHTunnelForwarder  # noqa: E402


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


class DataInclusionError(Exception):
    pass


def _parse_pkey(ssh_key: str, passphrase: str = "") -> paramiko.PKey:
    key_file = io.StringIO(ssh_key)
    pwd = passphrase or None
    for cls in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
        try:
            return cls.from_private_key(key_file, password=pwd)
        except paramiko.SSHException:
            key_file.seek(0)
    raise DataInclusionError("Unsupported SSH key format")


def execute_sql(
    database_url: str, ssh_host: str, ssh_user: str, ssh_key: str, sql: str, ssh_key_passphrase: str = ""
) -> QueryResult:
    """Open an SSH tunnel, run a single SQL query, close everything."""
    parsed = urlparse(database_url)
    remote_host = parsed.hostname
    remote_port = parsed.port or 5432

    emit_api_signal(source="data_inclusion", instance="datawarehouse", url=ssh_host, sql=sql)

    with SSHTunnelForwarder(
        ssh_host,
        ssh_username=ssh_user,
        ssh_pkey=_parse_pkey(ssh_key, ssh_key_passphrase),
        remote_bind_address=(remote_host, remote_port),
    ) as tunnel:
        conn = psycopg2.connect(
            host="127.0.0.1",
            port=tunnel.local_bind_port,
            dbname=parsed.path.lstrip("/"),
            user=parsed.username,
            password=parsed.password,
        )
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                columns = [desc[0] for desc in cur.description] if cur.description else []
                rows = [list(row) for row in cur.fetchall()] if columns else []
                return QueryResult(columns=columns, rows=rows, row_count=len(rows))
        finally:
            conn.close()
