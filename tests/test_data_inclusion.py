import paramiko

from lib.data_inclusion import QueryResult, _parse_pkey, execute_sql


def test_parse_pkey_tries_key_types_in_order(mocker):
    mocker.patch.object(paramiko.Ed25519Key, "from_private_key", side_effect=paramiko.SSHException)
    mock_key = mocker.MagicMock()
    mocker.patch.object(paramiko.RSAKey, "from_private_key", return_value=mock_key)

    assert _parse_pkey("key-content", passphrase="secret") is mock_key
    paramiko.RSAKey.from_private_key.assert_called_once()
    assert paramiko.RSAKey.from_private_key.call_args.kwargs["password"] == "secret"


def test_execute_sql_opens_tunnel_and_queries(mocker):
    mock_tunnel_cls = mocker.patch("lib.data_inclusion.SSHTunnelForwarder")
    mock_tunnel = mocker.MagicMock()
    mock_tunnel.local_bind_port = 54321
    mock_tunnel_cls.return_value.__enter__ = mocker.MagicMock(return_value=mock_tunnel)
    mock_tunnel_cls.return_value.__exit__ = mocker.MagicMock(return_value=False)

    mock_cursor = mocker.MagicMock()
    mock_cursor.description = [("id",), ("source",)]
    mock_cursor.fetchall.return_value = [("dora--abc", "dora")]
    mock_conn = mocker.MagicMock()
    mock_conn.cursor.return_value.__enter__ = mocker.MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = mocker.MagicMock(return_value=False)
    mocker.patch("lib.data_inclusion.psycopg2.connect", return_value=mock_conn)
    mocker.patch("lib.data_inclusion._parse_pkey", return_value=mocker.MagicMock())
    mocker.patch("lib.data_inclusion.emit_api_signal")

    result = execute_sql(
        database_url="postgresql://user:pass@remote-db:5432/di",
        ssh_host="bastion",
        ssh_user="deploy",
        ssh_key="key",
        sql="SELECT id, source FROM public_marts.marts__structures_v1 LIMIT 1",
    )

    assert result == QueryResult(columns=["id", "source"], rows=[["dora--abc", "dora"]], row_count=1)
    _, kwargs = mock_tunnel_cls.call_args
    assert kwargs["remote_bind_address"] == ("remote-db", 5432)
