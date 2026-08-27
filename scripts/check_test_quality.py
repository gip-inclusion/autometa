"""Rejette les tests creux : sans vérification ou avec assertion tautologique."""

import ast
import re
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


def main(paths):
    failed = False
    for path in _iter_test_files(paths):
        source = path.read_text()
        violations = check_source(source)
        if BROWSER_TESTS in path.parents:
            violations += check_dod_budget(source)
        for lineno, reason in violations:
            print(f"{path}:{lineno}: {reason}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["tests"]))
