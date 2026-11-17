"""Build Scalingo : post_compile ne laisse dans l'image que ce qui sert à l'exécution."""

import subprocess
from pathlib import Path

POST_COMPILE = Path(__file__).parent.parent / "bin" / "post_compile"

# Why: reproduit l'installeur du CLI, qui range le binaire sous ~/.local/share et pose un lien dans ~/.local/bin.
FAKE_INSTALLER = """#!/bin/bash
cat <<'EOF'
mkdir -p "$HOME/.local/share/claude/versions" "$HOME/.local/bin"
printf '#!/bin/bash\\necho 2.0.0\\n' > "$HOME/.local/share/claude/versions/2.0.0"
chmod +x "$HOME/.local/share/claude/versions/2.0.0"
ln -sf "$HOME/.local/share/claude/versions/2.0.0" "$HOME/.local/bin/claude"
EOF
"""


def run_post_compile(tmp_path: Path) -> Path:
    home, fake_bin = tmp_path / "build", tmp_path / "fake-bin"
    site_packages = home / ".scalingo" / "python" / "lib" / "python3.14" / "site-packages"
    for path in ("scipy/tests", "scipy/linalg/tests", "jinja2"):
        (site_packages / path).mkdir(parents=True)
    (site_packages / "scipy" / "linalg" / "basic.py").write_text("")
    (site_packages / "jinja2" / "tests.py").write_text("")
    fake_bin.mkdir()
    (fake_bin / "curl").write_text(FAKE_INSTALLER)
    (fake_bin / "curl").chmod(0o755)
    subprocess.run(
        [POST_COMPILE],
        check=True,
        capture_output=True,
        env={"HOME": str(home), "PATH": f"{fake_bin}:/usr/bin:/bin"},
    )
    return home


def test_post_compile_keeps_the_cli_but_drops_the_installer_copy(tmp_path):
    home = run_post_compile(tmp_path)

    assert subprocess.run([home / "bin" / "claude"], capture_output=True, text=True).stdout == "2.0.0\n"
    assert not (home / ".local" / "share" / "claude").exists()
    assert not (home / ".local" / "bin" / "claude").is_symlink()


def test_post_compile_drops_dependency_test_suites_but_not_modules_named_tests(tmp_path):
    site_packages = run_post_compile(tmp_path) / ".scalingo" / "python" / "lib" / "python3.14" / "site-packages"

    assert not (site_packages / "scipy" / "tests").exists()
    assert not (site_packages / "scipy" / "linalg" / "tests").exists()
    assert (site_packages / "scipy" / "linalg" / "basic.py").exists()
    assert (site_packages / "jinja2" / "tests.py").exists()
