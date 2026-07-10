"""Rejette les tests creux : sans vérification ou avec assertion tautologique."""

import ast
import sys
from pathlib import Path

SKIP_NAMES = {"skip", "skipif", "xfail"}


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
    return any(
        name == "raises" or name == "fail" or name.startswith("assert") for name in map(_call_name, _calls(node))
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
    test = node.test
    if isinstance(test, ast.Constant) and bool(test.value):
        return True
    if isinstance(test, ast.Compare) and len(test.comparators) == 1 and isinstance(test.ops[0], (ast.Eq, ast.Is)):
        return ast.dump(test.left) == ast.dump(test.comparators[0])
    return False


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
        for lineno, reason in check_source(path.read_text()):
            print(f"{path}:{lineno}: {reason}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["tests"]))
