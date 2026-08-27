"""Tests du garde-fou « un client de session HTTP porte un timeout » (angle mort de S113)."""

import importlib.util
from pathlib import Path

import pytest

from lib.rpe import TIMEOUT, http_client

_spec = importlib.util.spec_from_file_location(
    "check_http_timeouts", Path(__file__).parent.parent / "scripts" / "check_http_timeouts.py"
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def python_file(tmp_path, body):
    path = tmp_path / "client.py"
    path.write_text(body)
    return path


TIMED = "httpx.Client(timeout=30)\n"
TIMED_ASYNC = "httpx.AsyncClient(headers={}, timeout=httpx.Timeout(60, connect=10))\n"
TIMED_BY_NAME = "from httpx import Client\nClient(timeout=5)\n"
UNTIMED = "httpx.Client()\n"
UNTIMED_WITH_KWARGS = "httpx.Client(transport=transport)\n"
UNTIMED_ASYNC = "httpx.AsyncClient(base_url='https://x')\n"
UNTIMED_BY_NAME = "from httpx import AsyncClient\nAsyncClient()\n"
UNTIMED_SPLAT = "httpx.Client(**options)\n"
OTHER_CLIENT = "paramiko.SSHClient()\nboto3.client('s3')\n"


@pytest.mark.parametrize(
    ("source", "expected_lines"),
    [
        (TIMED, []),
        (TIMED_ASYNC, []),
        (TIMED_BY_NAME, []),
        (OTHER_CLIENT, []),
        (UNTIMED, [1]),
        (UNTIMED_WITH_KWARGS, [1]),
        (UNTIMED_ASYNC, [1]),
        (UNTIMED_BY_NAME, [2]),
        (UNTIMED_SPLAT, [1]),
    ],
)
def test_untimed_clients(tmp_path, source, expected_lines):
    found = _module.untimed_clients(python_file(tmp_path, source))
    assert [int(entry.rsplit(":", 1)[1]) for entry in found] == expected_lines


def test_scan_walks_the_tree_and_sorts(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text(UNTIMED)
    (tmp_path / "a.py").write_text(UNTIMED)
    assert _module.scan([tmp_path]) == [f"{tmp_path.as_posix()}/a.py:1", f"{tmp_path.as_posix()}/sub/b.py:1"]


def test_repository_has_no_untimed_session_client():
    assert _module.scan(_module.ROOTS) == []


def test_main_reports_the_offending_line(tmp_path, capsys, monkeypatch):
    (tmp_path / "a.py").write_text(UNTIMED)
    monkeypatch.setattr(_module, "ROOTS", (tmp_path,))
    assert _module.main() == 1
    assert "a.py:1" in capsys.readouterr().out


@pytest.mark.parametrize(("override", "expected"), [(None, TIMEOUT), (7, 7)])
def test_rpe_client_carries_a_read_timeout(override, expected):
    with http_client(timeout=override) as client:
        assert client.timeout.read == expected
