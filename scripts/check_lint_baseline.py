"""Gèle deux dettes de lint connues : elles se résorbent, elles ne s'étendent pas."""

# Ni les règles ruff S608/BLE001, ni les conventions de `.claude/rules/` ne peuvent être activées
# d'un coup — elles comptent des dizaines d'occurrences anciennes. Les activer sans baseline
# reviendrait à les laisser en `--exit-zero`, c'est-à-dire à ne rien vérifier.
#
# Les conventions étaient jusqu'ici vérifiées par un hook de session Claude Code seulement, alors
# que trois règles de `.claude/rules/` le citent comme leur vérificateur. Les faire passer par
# `make lint` est ce qui rend ces règles vraies pour tout le monde, agent ou humain.

import importlib.util
import json
import subprocess
import sys
import tomllib
from collections import Counter
from pathlib import Path

GATES = Path("gates.toml")
# Why: ruff rend des chemins résolus. Sans `resolve`, `relative_to` lève dès que la racine passe par
# un lien symbolique — un checkout sous /tmp, ou un worktree symlinké.
ROOT = Path(__file__).parent.parent.resolve()
HOOK = ROOT / ".claude" / "hooks" / "check_python.py"
# `data/` est écrit par l'agent, `skills/pdf/` est un skill vendored : ruff les exclut déjà.
NOT_OURS = (".venv", "data", "node_modules", "__pycache__", ".git", ".ruff_cache", "site-packages")
VENDORED = ("skills/pdf/",)


def read_baseline(path: Path) -> tuple[list[str], dict[str, int]]:
    section = tomllib.loads(path.read_text())["tool"]["lint_baseline"]
    return section["rules"], section["frozen"]


def read_conventions(path: Path) -> dict[str, int]:
    return tomllib.loads(path.read_text())["tool"]["python_conventions"]["frozen"]


def conventions_checker():
    """Le hook de conventions, chargé par son chemin — `.claude/hooks/` n'est pas un paquet."""
    spec = importlib.util.spec_from_file_location("check_python", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ours(path: Path, root: Path) -> bool:
    shown = path.relative_to(root).as_posix()
    return not any(part in NOT_OURS for part in path.relative_to(root).parts) and not shown.startswith(VENDORED)


def measure_conventions(root: Path) -> dict[str, int]:
    """Compte les violations des conventions Python du projet, par fichier."""
    checker = conventions_checker()
    return {shown: len(violations) for shown, violations in sorted(conventions(checker, root).items())}


def conventions(checker, root: Path) -> dict[str, list[str]]:
    """Les violations de conventions de chaque fichier du dépôt, par chemin."""
    found = {}
    for path in sorted(root.rglob("*.py")):
        if not ours(path, root):
            continue
        shown = path.relative_to(root).as_posix()
        try:
            source = path.read_text()
        except UnicodeDecodeError:
            continue
        if violations := checker.check(source, shown):
            found[shown] = violations
    return found


def measure(rules: list[str], root: Path) -> dict[str, int]:
    """Compte les violations de chaque règle gelée, par fichier."""
    done = subprocess.run(
        ["uv", "run", "--frozen", "ruff", "check", "--select", ",".join(rules), "--output-format=json", "--no-cache"],
        capture_output=True,
        text=True,
        check=False,
        cwd=root,
    )
    if done.returncode > 1:
        raise RuntimeError(f"ruff n'a pas pu mesurer {', '.join(rules)} : {done.stderr.strip()}")
    found = json.loads(done.stdout)
    resolved = root.resolve()
    return dict(Counter(f"{Path(i['filename']).relative_to(resolved).as_posix()}:{i['code']}" for i in found))


def report(found: dict[str, int], frozen: dict[str, int]) -> list[str]:
    problems = [
        f"Dette gelée en hausse : {key} passe de {frozen.get(key, 0)} à {count}\n"
        "  Cette dette se résorbe, elle ne s'étend pas — corriger, ou traiter le cas autrement."
        for key, count in sorted(found.items())
        if count > frozen.get(key, 0)
    ]
    return problems + [
        f"Entrée de baseline périmée : {key} descend de {count} à {found.get(key, 0)}\n"
        f"  Ramener la ligne de gates.toml à {found.get(key, 0)}, ou la supprimer — le gel suit la réparation."
        for key, count in sorted(frozen.items())
        if count > found.get(key, 0)
    ]


def detail(checker, root: Path, problems: list[str]) -> list[str]:
    """Les violations réelles des fichiers cités — un compte seul se répare à l'aveugle."""
    found = conventions(checker, root)
    return [
        f"  {shown} : {violation}"
        for shown, violations in found.items()
        if shown in "\n".join(problems)
        for violation in violations
    ]


def main() -> int:
    rules, frozen = read_baseline(ROOT / GATES)
    expected = read_conventions(ROOT / GATES)
    checker = conventions_checker()
    ruff_problems = report(measure(rules, ROOT), frozen)
    convention_problems = report(measure_conventions(ROOT), expected)
    if problems := ruff_problems + convention_problems:
        print("\n".join(problems))
        if convention_problems:
            print("\n".join(detail(checker, ROOT, convention_problems)))
        return 1
    ruff_total, convention_total = sum(frozen.values()), sum(expected.values())
    print(f"Dette gelée inchangée : {ruff_total} de ruff, {convention_total} de conventions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
