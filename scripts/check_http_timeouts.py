"""Refuse un client de session HTTP construit sans timeout."""

# S113 ne voit qu'un appel littéral sans timeout. Un httpx.Client() construit sans timeout puis
# réutilisé lui échappe — la forme de lib/matomo.py, lib/metabase.py, lib/rpe.py, lib/webinaires.py
# et lib/zendesk.py. Le timeout du constructeur est le seul filet pour un appel ajouté plus tard
# sans le repasser.

import ast
import sys
from pathlib import Path

ROOTS = (Path("web"), Path("lib"), Path("scripts"), Path("infra"), Path("tests"))
CLIENTS = {"Client", "AsyncClient"}


def is_client_call(node: ast.expr) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Attribute):
        return isinstance(node.func.value, ast.Name) and node.func.value.id == "httpx" and node.func.attr in CLIENTS
    return isinstance(node.func, ast.Name) and node.func.id in CLIENTS


def untimed_clients(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    return [
        f"{path.as_posix()}:{node.lineno}"
        for node in ast.walk(tree)
        if is_client_call(node) and not any(kw.arg == "timeout" for kw in node.keywords)
    ]


def scan(roots) -> list[str]:
    return sorted(
        entry
        for root in roots
        if root.exists()
        for path in sorted(root.rglob("*.py"))
        for entry in untimed_clients(path)
    )


def main() -> int:
    found = scan(ROOTS)
    if found:
        print(
            "\n".join(
                f"Client HTTP sans timeout : {entry}\n"
                "  Passer `timeout=` au constructeur — un appel ajouté plus tard hériterait sinon du défaut d'httpx."
                for entry in found
            )
        )
        return 1
    print("Tout client de session HTTP porte un timeout.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
