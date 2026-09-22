"""Un glob de préfixe ne voit pas les clusters de drapeaux courts : ce hook les voit."""

import importlib.util
from pathlib import Path

import pytest

_HOOK_PATH = Path(__file__).parent.parent / ".claude" / "hooks" / "guard_bash.py"
_spec = importlib.util.spec_from_file_location("guard_bash", _HOOK_PATH)
guard_bash = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard_bash)


@pytest.mark.parametrize(
    "commande",
    [
        "git commit --no-verify -m x",
        "git commit -m x --no-verify",
        "git commit -nm x",
        "git commit -am x -n",
        "git commit -n -m x",
        "git commit -amn x",
        'git add -A && git commit --no-verify -m "x"',
        "git   commit   --no-verify",
    ],
)
def test_un_commit_qui_desarme_les_hooks_est_refuse(commande):
    assert guard_bash.verdict(commande)


@pytest.mark.parametrize(
    "commande",
    [
        "git commit -m x",
        "git commit -am x",
        "git commit -q -F -",
        # Le corps d'un heredoc est de la donnée : un message de commit peut nommer le drapeau.
        "git commit -q -F - <<'EOF'\nfix: ne pas passer --no-verify\nEOF",
        "git commit -m x > /tmp/journal-n.txt",
        "git add -A",
        "git log --no-verify",
        "make test",
        "echo 'git commit --no-verify'",
        "",
    ],
)
def test_un_commit_nominal_passe(commande):
    assert guard_bash.verdict(commande) is None


def test_une_commande_non_analysable_ne_bloque_pas():
    """Fail-open sur un shlex qui casse : un guillemet impair n'a pas à geler la session."""
    assert guard_bash.verdict('git commit -m "impair') is None
