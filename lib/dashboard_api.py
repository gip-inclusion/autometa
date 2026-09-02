"""Façade des tableaux de bord — seul module de ce dépôt qu'un TDB a le droit d'importer."""

# Les tableaux de bord vivent sur S3, hors du dépôt : aucun diff ne les voit, donc aucun refactor
# ne peut mesurer ce qu'il casse chez eux. Plutôt que de courir après les cassures, on réduit la
# surface où elles peuvent se produire — cette façade est un contrat, ses tests en sont la preuve.

import ast

from lib import query
from lib.query import CallerType, QueryResult

__all__ = [
    "VERSION",
    "QueryResult",
    "facade_violations",
    "query_autometa_tables",
    "query_data_inclusion",
    "query_matomo",
    "query_metabase",
    "query_storage",
]

VERSION = 1

FACADE = "lib.dashboard_api"
APPLICATION_PACKAGES = ("lib", "web", "scripts", "skills", "infra")


def query_matomo(instance: str, method: str, params: dict | None = None, timeout: int = 180) -> QueryResult:
    """Interroge l'API Matomo. Renvoie un QueryResult, ne lève jamais."""
    return query.execute_matomo_query(
        instance=instance, caller=CallerType.APP, method=method, params=params, timeout=timeout
    )


def query_metabase(instance: str, sql: str | None = None, card_id: int | None = None, timeout: int = 60) -> QueryResult:
    """Interroge Metabase, par SQL ou par carte. Renvoie un QueryResult, ne lève jamais."""
    return query.execute_metabase_query(
        instance=instance, caller=CallerType.APP, sql=sql, card_id=card_id, timeout=timeout
    )


def query_data_inclusion(sql: str, timeout: int = 60) -> QueryResult:
    """Interroge le datawarehouse data·inclusion. Renvoie un QueryResult, ne lève jamais."""
    return query.execute_data_inclusion_query(sql=sql, caller=CallerType.APP, timeout=timeout)


def query_autometa_tables(sql: str, timeout: int = 60) -> QueryResult:
    """Interroge autometa_tables_db. Renvoie un QueryResult, ne lève jamais."""
    return query.execute_autometa_tables_query(sql=sql, caller=CallerType.APP, timeout=timeout)


def query_storage(sql: str, params: dict | None = None, timeout: int = 60) -> QueryResult:
    """Lit et écrit dans le schéma dashboard_storage. Renvoie un QueryResult, ne lève jamais."""
    return query.execute_dashboard_storage_query(sql=sql, caller=CallerType.APP, params=params, timeout=timeout)


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
