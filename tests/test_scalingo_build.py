"""Build Scalingo : le Chromium de verify_dashboard est installé par post_compile, pas par le Dockerfile."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
INSTALL = ROOT / "bin" / "install_playwright_browser.sh"


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

    assert "/install_playwright_browser.sh" in (ROOT / "bin" / "post_compile").read_text()
    assert buildpacks.index("https://github.com/Scalingo/apt-buildpack") < buildpacks.index(
        "https://github.com/Scalingo/python-buildpack"
    )
    assert {"libnss3", "libgbm1", "libxkbcommon0"} <= set((ROOT / "Aptfile").read_text().split())


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
