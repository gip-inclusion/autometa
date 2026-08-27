import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "check_route_auth", Path(__file__).parent.parent / "scripts" / "check_route_auth.py"
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def route_file(tmp_path, body):
    path = tmp_path / "routes.py"
    path.write_text(body)
    return path


PROTECTED = "@router.get('/x')\ndef page(user_email: str = Depends(get_current_user)):\n    pass\n"
PROTECTED_ANNOTATED = "@router.get('/x')\ndef page(u: Annotated[str, Depends(get_current_user)]):\n    pass\n"
PROTECTED_BY_NAME = "@router.get('/x')\ndef page(u: str = Depends(get_current_user_name)):\n    pass\n"
UNPROTECTED = "@router.get('/x')\ndef page():\n    pass\n"
UNPROTECTED_ASYNC = "@router.post('/x')\nasync def page(request: Request):\n    pass\n"
OTHER_DEPENDENCY = "@router.get('/x')\ndef page(db = Depends(get_db)):\n    pass\n"
APP_DECORATOR = "@app.delete('/x')\ndef page():\n    pass\n"
API_ROUTE = "@router.api_route('/x', methods=['POST'])\ndef page():\n    pass\n"
NOT_A_ROUTE = "@functools.cache\ndef page():\n    pass\n"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (PROTECTED, []),
        (PROTECTED_ANNOTATED, []),
        (PROTECTED_BY_NAME, []),
        (NOT_A_ROUTE, []),
        (UNPROTECTED, ["page"]),
        (UNPROTECTED_ASYNC, ["page"]),
        (OTHER_DEPENDENCY, ["page"]),
        (APP_DECORATOR, ["page"]),
        (API_ROUTE, ["page"]),
    ],
)
def test_unprotected_routes(tmp_path, source, expected):
    found = _module.unprotected_routes(route_file(tmp_path, source))
    assert [entry.split(":")[1] for entry in found] == expected


def test_scan_walks_the_tree_and_sorts(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "b.py").write_text(UNPROTECTED)
    (tmp_path / "sub" / "a.py").write_text(UNPROTECTED)
    assert _module.scan(tmp_path) == [f"{tmp_path.as_posix()}/b.py:page", f"{tmp_path.as_posix()}/sub/a.py:page"]


@pytest.mark.parametrize(
    ("found", "allowlist", "expected_count"),
    [
        (["a.py:x"], {"a.py:x"}, 0),
        ([], set(), 0),
        (["a.py:x"], set(), 1),
        ([], {"a.py:x"}, 1),
        (["a.py:x", "a.py:y"], {"a.py:z"}, 3),
    ],
)
def test_report(found, allowlist, expected_count):
    assert len(_module.report(found, allowlist)) == expected_count


def test_report_tells_how_to_protect_a_new_route():
    assert "Depends(get_current_user)" in _module.report(["a.py:x"], set())[0]


def test_report_tells_how_to_clear_a_stale_entry():
    assert "gates.toml" in _module.report([], {"a.py:x"})[0]


def test_baseline_matches_the_routes_actually_exposed(monkeypatch):
    monkeypatch.chdir(Path(__file__).parent.parent)
    assert _module.main() == 0


def test_main_fails_when_a_route_escapes_the_baseline(mocker, tmp_path, capsys):
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "routes.py").write_text(UNPROTECTED)
    (tmp_path / "gates.toml").write_text("[tool.route_auth]\nallowlist = []\n")
    mocker.patch.object(_module, "WEB", tmp_path / "web")
    mocker.patch.object(_module, "GATES", tmp_path / "gates.toml")
    assert _module.main() == 1
    assert "Route sans authentification" in capsys.readouterr().out
