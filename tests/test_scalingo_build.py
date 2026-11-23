"""Build Scalingo : Chromium (verify_dashboard) et merman-cli viennent de post_compile, pas du Dockerfile."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
INSTALL = ROOT / "bin" / "install_playwright_browser.sh"
MERMAN = ROOT / "bin" / "install_merman.sh"


def fake_curl(directory: Path) -> Path:
    """Un curl qui écrit, à la place de toute archive demandée, un contenu qui n'est pas celui attendu."""
    directory.mkdir()
    curl = directory / "curl"
    curl.write_text('#!/bin/bash\nwhile [ "$1" != "-o" ]; do shift; done\necho "autre chose" > "$2"\n')
    curl.chmod(0o755)
    return directory


def run_merman_install(monkeypatch, home: Path, bin_dir: Path) -> subprocess.CompletedProcess:
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", str(bin_dir), prepend=":")
    return subprocess.run([MERMAN], capture_output=True, text=True, check=False)


def test_post_compile_installs_merman_and_only_warns_when_it_cannot():
    post_compile = (ROOT / "bin" / "post_compile").read_text()

    assert '/install_merman.sh" \\\n    || echo "-----> WARNING' in post_compile


def test_an_archive_that_is_not_the_pinned_one_is_refused_and_nothing_is_installed(tmp_path, monkeypatch):
    home = tmp_path / "app"
    home.mkdir()

    done = run_merman_install(monkeypatch, home, fake_curl(tmp_path / "bin"))

    assert done.returncode != 0
    assert "empreinte inattendue" in done.stderr
    assert not (home / ".merman").exists()


def test_merman_already_installed_at_the_pinned_version_is_not_downloaded_again(tmp_path, monkeypatch):
    merman = tmp_path / "app" / ".merman"
    merman.mkdir(parents=True)
    version = next(line for line in MERMAN.read_text().splitlines() if line.startswith("VERSION=")).split("=")[1]
    (merman / "merman-cli").write_text(f'#!/bin/bash\necho "merman-cli {version}"\n')
    (merman / "merman-cli").chmod(0o755)
    (merman / "DejaVuSans-Bold.ttf").write_text("")

    done = run_merman_install(monkeypatch, tmp_path / "app", fake_curl(tmp_path / "bin"))

    assert done.returncode == 0
    assert "already in" in done.stdout


def fake_python(directory: Path) -> Path:
    directory.mkdir()
    python = directory / "python"
    python.write_text('#!/bin/bash\necho "$@" >> "$HOME/calls"\nmkdir -p "$PLAYWRIGHT_BROWSERS_PATH/chromium"\n')
    python.chmod(0o755)
    return directory


def run_install(monkeypatch, home: Path, bin_dir: Path, cache: Path) -> None:
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CACHE_DIR", str(cache))
    monkeypatch.setenv("PATH", str(bin_dir), prepend=":")
    subprocess.run([INSTALL], check=True, capture_output=True)


def test_post_compile_installs_the_browser_after_the_apt_libraries():
    buildpacks = (ROOT / ".buildpacks").read_text().split()
    packages = {line for line in (ROOT / "Aptfile").read_text().splitlines() if line and not line.startswith("#")}

    assert "/install_playwright_browser.sh" in (ROOT / "bin" / "post_compile").read_text()
    assert buildpacks.index("https://github.com/Scalingo/apt-buildpack") < buildpacks.index(
        "https://github.com/Scalingo/python-buildpack"
    )
    assert {"libnss3", "libgbm1", "libxkbcommon0", "libasound2-dev"} <= packages
    # Why: sans candidat sur scalingo-24, ce nom fait échouer tout le build.
    assert "libasound2" not in packages


def test_install_puts_chromium_where_the_runtime_looks_and_caches_it(tmp_path, monkeypatch):
    home, cache = tmp_path / "app", tmp_path / "cache"
    home.mkdir()
    cache.mkdir()

    run_install(monkeypatch, home, fake_python(tmp_path / "bin"), cache)

    assert (home / "calls").read_text() == "-m playwright install --only-shell chromium\n"
    assert (home / ".playwright" / "chromium").is_dir()
    assert (cache / "playwright" / "chromium").is_dir()
    assert (
        home / ".profile.d" / "playwright.sh"
    ).read_text() == 'export PLAYWRIGHT_BROWSERS_PATH="$HOME/.playwright"\n'


def test_install_restores_the_cached_browsers_before_installing(tmp_path, monkeypatch):
    home, cache = tmp_path / "app", tmp_path / "cache"
    home.mkdir()
    (cache / "playwright" / "chromium_headless_shell-1243").mkdir(parents=True)

    run_install(monkeypatch, home, fake_python(tmp_path / "bin"), cache)

    assert (home / ".playwright" / "chromium_headless_shell-1243").is_dir()
