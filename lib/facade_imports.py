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


def dotted_name(node: ast.AST) -> list[str] | None:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute) and (base := dotted_name(node.value)):
        return [*base, node.attr]
    return None


def imported_symbols(source: str) -> list[str]:
    """Symboles applicatifs qu'un script utilise (`lib.query.CallerType.APP`), façade comprise. Lève sur source illisible."""
    tree = ast.parse(source)
    bound, used = {}, set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in APPLICATION_PACKAGES:
                    used.add(alias.name)
                    bound[alias.asname or root] = alias.name if alias.asname else root
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            if node.module.split(".")[0] in APPLICATION_PACKAGES:
                names = {alias.asname or alias.name: f"{node.module}.{alias.name}" for alias in node.names}
                bound |= names
                used |= set(names.values())
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and (parts := dotted_name(node)) and parts[0] in bound:
            used.add(".".join([bound[parts[0]], *parts[1:]]))
    return sorted(used)
