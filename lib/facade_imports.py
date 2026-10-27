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


def rebound_names(tree: ast.AST) -> set[str]:
    """Noms qu'un script réaffecte quelque part (paramètre, affectation, boucle, définition, `except … as`)."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load):
            names.add(node.id)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
    return names


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
    # Why: sans suivi des portées, `def f(query): query.strip()` ferait croire à `lib.query.strip` ;
    # un nom réaffecté n'est donc suivi que jusqu'à son import, jamais dans ses attributs.
    traced = bound.keys() - rebound_names(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and (parts := dotted_name(node)) and parts[0] in traced:
            used.add(".".join([bound[parts[0]], *parts[1:]]))
    return sorted(used)
