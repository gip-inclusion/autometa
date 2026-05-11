"""Client for the data·inclusion datawarehouse (PostgreSQL via SSH tunnel)."""

import io
from contextlib import contextmanager
from urllib.parse import urlparse

import paramiko
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

# sshtunnel 0.4.0 references paramiko.DSSKey which was removed in paramiko 4.0
if not hasattr(paramiko, "DSSKey"):
    paramiko.DSSKey = None

from sshtunnel import SSHTunnelForwarder  # noqa: E402

from .api_signals import emit_api_signal
from .pg import QueryResult


class SSHError(Exception):
    pass


def _parse_pkey(ssh_key: str, passphrase: str = "") -> paramiko.PKey:
    key_file = io.StringIO(ssh_key)
    pwd = passphrase or None
    for cls in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
        try:
            return cls.from_private_key(key_file, password=pwd)
        except paramiko.SSHException:
            key_file.seek(0)
    raise SSHError("Unsupported SSH key format")


@contextmanager
def _open_tunnel(database_url: str, ssh_host: str, ssh_user: str, ssh_key: str, ssh_key_passphrase: str = ""):
    parsed = urlparse(database_url)
    with SSHTunnelForwarder(
        ssh_host,
        ssh_username=ssh_user,
        ssh_pkey=_parse_pkey(ssh_key, ssh_key_passphrase),
        remote_bind_address=(parsed.hostname, parsed.port or 5432),
    ) as tunnel:
        yield parsed, tunnel


def execute_sql(
    database_url: str, ssh_host: str, ssh_user: str, ssh_key: str, sql: str, ssh_key_passphrase: str = ""
) -> QueryResult:
    """Open an SSH tunnel, run a single SQL query, close everything."""
    emit_api_signal(source="data_inclusion", instance="datawarehouse", url=ssh_host, sql=sql)
    with _open_tunnel(database_url, ssh_host, ssh_user, ssh_key, ssh_key_passphrase) as (parsed, tunnel):
        url = f"postgresql://{parsed.username}:{parsed.password}@127.0.0.1:{tunnel.local_bind_port}/{parsed.path.lstrip('/')}"
        engine = create_engine(url, poolclass=NullPool)
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [list(row) for row in result.fetchall()]
            return QueryResult(columns=columns, rows=rows, row_count=len(rows))
