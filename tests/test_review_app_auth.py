"""Le second mode d'entrée du proxy : armé sur les seules review apps, jamais ailleurs."""

import subprocess
from pathlib import Path

import pytest

SCRIPT = str(Path("bin/with_review_app_auth.sh").resolve())
HTPASSWD_LINE = "e2e:$2y$05$notarealhashjustatestfixture"
PRINT_FILE_PATH = ["sh", "-c", 'printf "%s" "${OAUTH2_PROXY_HTPASSWD_FILE:-}"']


def run_script(**env: str) -> str:
    result = subprocess.run(
        [SCRIPT, *PRINT_FILE_PATH], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", **env}, check=True
    )
    return result.stdout


@pytest.mark.parametrize(
    "env",
    [
        pytest.param({"AUTOMETA_ENV": "review"}, id="review sans secret"),
        pytest.param({"AUTOMETA_ENV": "staging", "REVIEW_APP_HTPASSWD": HTPASSWD_LINE}, id="staging"),
        pytest.param({"AUTOMETA_ENV": "prod", "REVIEW_APP_HTPASSWD": HTPASSWD_LINE}, id="prod"),
        pytest.param({"REVIEW_APP_HTPASSWD": HTPASSWD_LINE}, id="environnement non renseigné"),
    ],
)
def test_no_second_entry_mode_outside_a_review_app(env):
    assert run_script(**env) == ""


def test_a_review_app_gets_its_secrets_file_written_at_boot():
    path = Path(run_script(AUTOMETA_ENV="review", REVIEW_APP_HTPASSWD=HTPASSWD_LINE))

    assert path.read_text() == HTPASSWD_LINE + "\n"
    assert path.stat().st_mode & 0o077 == 0
    path.unlink()
