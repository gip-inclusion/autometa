"""Ce qu'un tableau de bord importe — stdlib seule, pour que les hooks de garde puissent le lire."""

import ast

FACADE = "lib.dashboard_api"
APPLICATION_PACKAGES = ("lib", "web", "scripts", "skills", "infra")


def imported_modules(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            if node.module in APPLICATION_PACKAGES:
                yield from (f"{node.module}.{alias.name}" for alias in node.names)
            else:
                yield node.module


def facade_violations(source: str) -> list[str]:
    """Modules applicatifs qu'un tableau de bord importe hors de la façade. Lève sur source illisible."""
    return sorted({
        module
        for module in imported_modules(ast.parse(source))
        if module.split(".")[0] in APPLICATION_PACKAGES and module != FACADE
    })
