"""Signale une migration qui pose une contrainte non nulle sans remplir les lignes existantes."""

import ast
import sys
from pathlib import Path

VERSIONS = Path("alembic/versions")


def poses_not_null(call: ast.Call) -> bool:
    """`alter_column(nullable=False)` ou `add_column` d'une colonne non nulle sans server_default."""
    name = call.func.attr if isinstance(call.func, ast.Attribute) else None
    if name == "alter_column":
        return any(
            kw.arg == "nullable" and kw.value.value is False
            for kw in call.keywords
            if isinstance(kw.value, ast.Constant)
        )
    if name == "add_column":
        column = next((arg for arg in call.args if isinstance(arg, ast.Call)), None)
        if column is None:
            return False
        return "server_default" not in {kw.arg for kw in column.keywords} and any(
            kw.arg == "nullable" and isinstance(kw.value, ast.Constant) and kw.value.value is False
            for kw in column.keywords
        )
    return False


def unbackfilled_columns(source: str) -> list[str]:
    """Contraintes non nulles posées avant tout `op.execute` dans le même `upgrade()`."""
    upgrade = next(
        (node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == "upgrade"),
        None,
    )
    if upgrade is None:
        return []

    backfilled = False
    problems = []
    for node in ast.walk(upgrade):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == "execute":
            backfilled = True
        elif poses_not_null(node) and not backfilled:
            table = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else "?"
            column = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else "?"
            problems.append(f"{table}.{column}")
    return problems


def main() -> int:
    migrations = sorted(VERSIONS.glob("*.py"))
    signalled = {path.name: columns for path in migrations if (columns := unbackfilled_columns(path.read_text()))}
    if not signalled:
        print(f"{len(migrations)} migrations, aucune contrainte non nulle sans backfill.")
        return 0

    for name, columns in signalled.items():
        print(f"{name} — {', '.join(columns)}")
    print(
        "\nLe job Migrations tourne sur une base vide : une contrainte non nulle y passe toujours, et "
        "échoue en production sur les lignes déjà présentes. Remplir ces colonnes par un `op.execute` "
        "de mise à jour, avant, dans le même `upgrade()`."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
