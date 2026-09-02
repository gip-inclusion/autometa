import importlib.util
import subprocess
from pathlib import Path

import httpx
import pytest
import redis
from sqlalchemy.exc import OperationalError

_spec = importlib.util.spec_from_file_location("doctor", Path(__file__).parent.parent / "scripts" / "doctor.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

DB_URL = "postgresql://autometa:autometa@localhost:5432/autometa"


def completed(returncode, stdout=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


@pytest.mark.parametrize(
    ("which", "returncode", "expected_fragment"),
    [
        (None, 0, "Docker n'est pas installé"),
        ("/usr/bin/docker", 1, "ne tourne pas"),
        ("/usr/bin/docker", 0, None),
    ],
)
def test_check_docker(mocker, which, returncode, expected_fragment):
    mocker.patch.object(_module.shutil, "which", return_value=which)
    mocker.patch.object(_module.subprocess, "run", return_value=completed(returncode))
    problem = _module.check_docker({})
    assert (expected_fragment in problem) if expected_fragment else (problem is None)


def test_check_postgres_without_url():
    assert "DATABASE_URL est absent" in _module.check_postgres({})


def test_check_postgres_unreachable(mocker):
    mocker.patch.object(_module.sqlalchemy, "create_engine", side_effect=OperationalError("", {}, Exception()))
    assert "localhost:5432" in _module.check_postgres({"DATABASE_URL": DB_URL})


def test_check_postgres_reachable(mocker):
    mocker.patch.object(_module.sqlalchemy, "create_engine", return_value=mocker.MagicMock())
    assert _module.check_postgres({"DATABASE_URL": DB_URL}) is None


@pytest.mark.parametrize(
    ("side_effect", "expected_fragment"),
    [(redis.RedisError(), "Redis ne répond pas"), (None, None)],
)
def test_check_redis(mocker, side_effect, expected_fragment):
    mocker.patch.object(_module.redis, "from_url", side_effect=side_effect, return_value=mocker.MagicMock())
    problem = _module.check_redis({})
    assert (expected_fragment in problem) if expected_fragment else (problem is None)


@pytest.mark.parametrize(
    ("settings", "side_effect", "expected_fragment"),
    [
        ({}, None, None),
        ({"S3_ENDPOINT": "http://localhost:9000"}, httpx.ConnectError(""), "ne répond pas"),
        ({"S3_ENDPOINT": "http://localhost:9000"}, None, None),
    ],
)
def test_check_object_storage(mocker, settings, side_effect, expected_fragment):
    mocker.patch.object(_module.httpx, "get", side_effect=side_effect)
    problem = _module.check_object_storage(settings)
    assert (expected_fragment in problem) if expected_fragment else (problem is None)


@pytest.mark.parametrize(
    ("process", "expected_fragment"),
    [
        (completed(1), "illisible"),
        (completed(0, "abc123"), "pas à jour"),
        (completed(0, "abc123 (head)"), None),
    ],
)
def test_check_migrations(mocker, process, expected_fragment):
    mocker.patch.object(_module.subprocess, "run", return_value=process)
    problem = _module.check_migrations({})
    assert (expected_fragment in problem) if expected_fragment else (problem is None)


@pytest.mark.parametrize(
    ("settings", "which", "expected_fragment"),
    [
        ({"AGENT_BACKEND": "cli-ollama"}, None, None),
        ({}, None, "CLI Claude Code est absente"),
        ({}, "/usr/local/bin/claude", None),
    ],
)
def test_check_agent_cli(mocker, settings, which, expected_fragment):
    mocker.patch.object(_module.shutil, "which", return_value=which)
    problem = _module.check_agent_cli(settings)
    assert (expected_fragment in problem) if expected_fragment else (problem is None)


@pytest.mark.parametrize(
    ("settings", "credentials_exist", "expected_fragment"),
    [
        ({"CLAUDE_CODE_OAUTH_TOKEN": "tok"}, False, None),
        ({}, True, None),
        ({}, False, "n'est pas authentifié"),
    ],
)
def test_warn_agent_auth(mocker, tmp_path, settings, credentials_exist, expected_fragment):
    credentials = tmp_path / ".credentials.json"
    if credentials_exist:
        credentials.write_text("{}")
    mocker.patch.object(_module, "CREDENTIALS_FILE", credentials)
    problem = _module.warn_agent_auth(settings)
    assert (expected_fragment in problem) if expected_fragment else (problem is None)


@pytest.mark.parametrize(
    ("settings", "expected_fragment"),
    [
        ({"MATOMO_API_KEY": "a", "METABASE_STATS_API_KEY": "b"}, None),
        ({"MATOMO_API_KEY": "a"}, "METABASE_STATS_API_KEY"),
        ({}, "MATOMO_API_KEY"),
    ],
)
def test_warn_data_sources(settings, expected_fragment):
    problem = _module.warn_data_sources(settings)
    assert (expected_fragment in problem) if expected_fragment else (problem is None)


@pytest.mark.parametrize(
    ("which", "biome_installed", "expected_fragment"),
    [
        (None, False, "Node.js"),
        ("/usr/local/bin/npm", False, "make lint-js"),
        ("/usr/local/bin/npm", True, None),
    ],
)
def test_warn_front_tells_what_is_missing_before_biome_can_run(
    mocker, tmp_path, which, biome_installed, expected_fragment
):
    biome = tmp_path / "biome"
    if biome_installed:
        biome.write_text("")
    mocker.patch.object(_module.shutil, "which", return_value=which)
    mocker.patch.object(_module, "BIOME", biome)

    problem = _module.warn_front({})

    assert (expected_fragment in problem) if expected_fragment else (problem is None)


@pytest.mark.parametrize("installed", ["chromium-1234", None])
def test_warn_browser_looks_where_playwright_actually_ranges_its_browsers(tmp_path, installed):
    """Le navigateur ne bloque pas le parcours : seule la présence du test sous `browser/` est exigée."""
    if installed:
        (tmp_path / installed).mkdir()

    problem = _module.warn_browser({"PLAYWRIGHT_BROWSERS_PATH": str(tmp_path)})

    assert (problem is None) if installed else ("make browsers" in problem)


def test_the_playwright_cache_defaults_to_the_place_of_the_platform(mocker):
    mocker.patch.object(_module.sys, "platform", "linux")

    assert _module.playwright_cache({}) == Path.home() / ".cache" / "ms-playwright"


def test_the_front_and_the_browser_are_notes_not_breakages():
    """Rendre le parcours otage de Node ou de Playwright, c'est ce qu'on a refusé pour Docker."""
    named = [label for label, _ in _module.OPTIONAL]

    assert {"Front", "Navigateur"} <= set(named)
    assert not {"Front", "Navigateur"} & {label for label, _ in _module.REQUIRED}


def test_run_reports_every_failure_it_met(capsys):
    checks = [("A", lambda _: None), ("B", lambda _: "cassé")]
    assert _module.run(checks, {}, "PANNE") == ["cassé"]
    assert "cassé" in capsys.readouterr().out


def env_file(mocker, tmp_path, exists):
    path = tmp_path / ".env"
    if exists:
        path.write_text("")
    mocker.patch.object(_module, "ENV_FILE", path)


def test_main_stops_on_missing_env_file(mocker, tmp_path, capsys):
    env_file(mocker, tmp_path, exists=False)
    assert _module.main() == 1
    assert "make setup" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("required", "expected_code"),
    [([("A", lambda _: "cassé")], 1), ([("A", lambda _: None)], 0)],
)
def test_main_returns_the_verdict_of_the_required_checks(mocker, tmp_path, required, expected_code):
    env_file(mocker, tmp_path, exists=True)
    mocker.patch.object(_module, "REQUIRED", required)
    mocker.patch.object(_module, "OPTIONAL", [])
    assert _module.main() == expected_code


def last_line(capsys) -> str:
    """La dernière ligne est celle que le journal du parcours retient d'une panne d'environnement."""
    return [line for line in capsys.readouterr().out.splitlines() if line.strip()][-1]


def test_the_verdict_carries_the_gesture_to_make_not_only_the_count(mocker, tmp_path, capsys):
    """« 4 point(s) à corriger » ne dit ni lesquels ni quoi faire : c'est le geste qui débloque."""
    env_file(mocker, tmp_path, exists=True)
    mocker.patch.object(_module, "REQUIRED", [("A", lambda _: "Ouvrez Docker, puis relancez `make doctor`.")])
    mocker.patch.object(_module, "OPTIONAL", [])

    _module.main()

    assert last_line(capsys) == "1 point à corriger. Commencer par : Ouvrez Docker, puis relancez `make doctor`."


def test_the_verdict_counts_every_breakage_and_names_the_first_to_repair(mocker, tmp_path, capsys):
    env_file(mocker, tmp_path, exists=True)
    mocker.patch.object(
        _module, "REQUIRED", [("A", lambda _: "Ouvrez Docker."), ("B", lambda _: "Lancez `make setup`.")]
    )
    mocker.patch.object(_module, "OPTIONAL", [])

    _module.main()

    assert last_line(capsys) == "2 points à corriger. Commencer par : Ouvrez Docker."


def test_a_ready_environment_ends_on_a_line_that_asks_for_nothing(mocker, tmp_path, capsys):
    env_file(mocker, tmp_path, exists=True)
    mocker.patch.object(_module, "REQUIRED", [("A", lambda _: None)])
    mocker.patch.object(_module, "OPTIONAL", [])

    _module.main()

    assert last_line(capsys) == "Environnement prêt."
