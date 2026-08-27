"""Rejette les tests creux : sans vérification ou avec assertion tautologique."""

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

SKIP_NAMES = {"skip", "skipif", "xfail"}

BROWSER_TESTS = Path("browser")
DOD_TEST = re.compile(r"test_dod_\d+")
# Sans borne, le coût récurrent de L3 suit la verbosité de la demande — voir docs/paved-road/l3-e2e.md.
MAX_DOD_CRITERIA = 5


def _is_test(node):
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")


def _call_name(call):
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _calls(node):
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)]


def _has_verification(node):
    if any(isinstance(n, ast.Assert) for n in ast.walk(node)):
        return True
    # `expect` : les assertions Playwright ne passent pas par `assert`.
    return any(
        name in {"raises", "fail", "expect"} or name.startswith("assert") for name in map(_call_name, _calls(node))
    )


def _is_skipped(node):
    for deco in node.decorator_list:
        for n in ast.walk(deco):
            if isinstance(n, ast.Name) and n.id in SKIP_NAMES:
                return True
            if isinstance(n, ast.Attribute) and n.attr in SKIP_NAMES:
                return True
    return any(_call_name(call) == "skip" for call in _calls(node))


def _is_tautological(node):
    # str literals et self-comparaisons sont couverts par ruff (PLW0129 / PLR0124) ; ici : assert True, assert 1…
    test = node.test
    return isinstance(test, ast.Constant) and bool(test.value) and not isinstance(test.value, str)


def check_source(source):
    violations = []
    for node in ast.walk(ast.parse(source)):
        if not _is_test(node) or _is_skipped(node):
            continue
        if not _has_verification(node):
            violations.append((node.lineno, "test sans vérification (ni assert, ni raises, ni mock.assert_*)"))
        for assertion in (n for n in ast.walk(node) if isinstance(n, ast.Assert)):
            if _is_tautological(assertion):
                violations.append((assertion.lineno, "assertion tautologique (toujours vraie)"))
    return violations


def _porte_une_raison(node):
    """`reason=` sur le marqueur, le mécanisme natif de pytest, vaut explication."""
    return any(
        kw.arg == "reason" and isinstance(kw.value, ast.Constant) and kw.value.value
        for deco in node.decorator_list
        for n in ast.walk(deco)
        if isinstance(n, ast.Call)
        for kw in n.keywords
    )


def skips_sans_raison(source):
    """Un `skip`/`xfail` ajouté sans dire pourquoi éteint un test que personne ne rallumera."""
    lignes = source.split("\n")
    violations = []
    for node in ast.walk(ast.parse(source)):
        if not _is_test(node) or not _is_skipped(node) or _porte_une_raison(node):
            continue
        debut = min([deco.lineno for deco in node.decorator_list] or [node.lineno]) - 1
        voisinage = "\n".join(lignes[max(0, debut - 2) : node.lineno])
        if "# Why:" not in voisinage:
            violations.append((
                node.lineno,
                f"`{node.name}` est désactivé sans `reason=` ni `# Why:` — dire ce qu'on attend pour le rallumer",
            ))
    return violations


def assertions_affaiblies(source, source_base):
    """Compte les assertions par test : en perdre sur un test préexistant, c'est le désarmer."""

    def par_test(texte):
        return {
            node.name: sum(1 for n in ast.walk(node) if isinstance(n, ast.Assert | ast.Raise))
            + sum(1 for call in _calls(node) if (_call_name(call) or "").startswith("assert"))
            for node in ast.walk(ast.parse(texte))
            if _is_test(node)
        }

    avant, apres = par_test(source_base), par_test(source)
    return [
        (0, f"`{nom}` passe de {avant[nom]} à {apres[nom]} assertion(s) : reprendre, ou demander un break-glass")
        for nom in avant
        if nom in apres and apres[nom] < avant[nom]
    ]


def version_sur_la_base(path, base):
    """Le fichier tel qu'il est sur la base de comparaison, ou None s'il y est absent."""
    done = subprocess.run(["git", "show", f"{base}:{path}"], capture_output=True, text=True, check=False)
    return done.stdout if done.returncode == 0 else None


def check_dod_budget(source):
    """Au-delà de cinq critères démontrés par navigateur, la preuve doit retomber sur une forme moins coûteuse."""
    dod_tests = sorted(
        (n for n in ast.walk(ast.parse(source)) if _is_test(n) and DOD_TEST.fullmatch(n.name)),
        key=lambda node: node.lineno,
    )
    return [
        (node.lineno, f"plus de {MAX_DOD_CRITERIA} critères démontrés par un parcours de navigateur")
        for node in dod_tests[MAX_DOD_CRITERIA:]
    ]


def _iter_test_files(paths):
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            yield from sorted(path.rglob("test_*.py"))
        elif path.name.startswith("test_") and path.suffix == ".py":
            yield path


def main(paths, base=None):
    failed = False
    # Why: un fichier absent de la base est normal (test neuf) ; une base illisible ne l'est pas,
    # et laisserait le check passer sans rien comparer. On distingue les deux une fois pour toutes.
    if base and subprocess.run(["git", "rev-parse", "--verify", base], capture_output=True, check=False).returncode:
        print(f"Base « {base} » illisible : les assertions affaiblies ne sont pas comparées.", file=sys.stderr)
        base = None
    for path in _iter_test_files(paths):
        source = path.read_text()
        violations = check_source(source) + skips_sans_raison(source)
        if BROWSER_TESTS in path.parents:
            violations += check_dod_budget(source)
        if base and (avant := version_sur_la_base(path, base)):
            violations += assertions_affaiblies(source, avant)
        for lineno, reason in violations:
            print(f"{path}:{lineno}: {reason}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", default=["tests"])
    parser.add_argument("--base", help="référence git : compare les assertions des tests préexistants")
    arguments = parser.parse_args()
    sys.exit(main(arguments.paths or ["tests"], arguments.base))
