"""Refuse une route FastAPI neuve sans dépendance d'authentification."""

# L'autorisation est écrite route par route dans cette application : une route neuve naît
# sans protection. Les routes déjà exposées forment une baseline gelée dans gates.toml.

import ast
import sys
import tomllib
from pathlib import Path

WEB = Path("web")
GATES = Path("gates.toml")
HTTP_VERBS = {"get", "post", "put", "patch", "delete", "head", "options", "api_route", "websocket"}
AUTH_DEPENDENCIES = {"get_current_user", "get_current_user_name"}


def is_route_decorator(node: ast.expr) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in HTTP_VERBS


def depends_on_auth(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Couvre `x = Depends(auth)` comme `x: Annotated[str, Depends(auth)]`."""
    for node in ast.walk(func.args):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "Depends"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id in AUTH_DEPENDENCIES
        ):
            return True
    return False


def unprotected_routes(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    return [
        f"{path.as_posix()}:{node.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and any(is_route_decorator(d) for d in node.decorator_list)
        and not depends_on_auth(node)
    ]


def scan(root: Path) -> list[str]:
    return sorted(route for path in sorted(root.rglob("*.py")) for route in unprotected_routes(path))


def read_allowlist(path: Path) -> set[str]:
    return set(tomllib.loads(path.read_text())["tool"]["route_auth"]["allowlist"])


def report(found: list[str], allowlist: set[str]) -> list[str]:
    problems = [
        f"Route sans authentification : {route}\n"
        "  Ajouter `user_email: str = Depends(get_current_user)` à sa signature."
        for route in found
        if route not in allowlist
    ]
    problems += [
        f"Entrée de baseline périmée : {route}\n  Cette route est protégée — supprimer la ligne de gates.toml."
        for route in sorted(allowlist - set(found))
    ]
    return problems


def main() -> int:
    problems = report(scan(WEB), read_allowlist(GATES))
    if problems:
        print("\n".join(problems))
        return 1
    print("Aucune route exposée hors de la baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
