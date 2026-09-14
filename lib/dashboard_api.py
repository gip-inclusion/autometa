"""Façade des tableaux de bord — seul module de ce dépôt qu'un TDB a le droit d'importer."""

# Les tableaux de bord vivent sur S3, hors du dépôt : aucun diff ne les voit, donc aucun refactor
# ne peut mesurer ce qu'il casse chez eux. Plutôt que de courir après les cassures, on réduit la
# surface où elles peuvent se produire — cette façade est un contrat, ses tests en sont la preuve.

from lib import query
from lib.datadog import by_count
from lib.facade_imports import APPLICATION_PACKAGES, FACADE, facade_violations
from lib.query import CallerType, QueryResult

__all__ = [
    "APPLICATION_PACKAGES",
    "FACADE",
    "VERSION",
    "QueryResult",
    "by_count",
    "count_datadog",
    "facade_violations",
    "query_autometa_tables",
    "query_data_inclusion",
    "query_datadog",
    "query_matomo",
    "query_metabase",
    "query_storage",
    "sample_datadog",
]

VERSION = 1


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


def query_datadog(
    search: str,
    days: int = 7,
    group_by: list[str | dict] | None = None,
    compute: list[dict] | None = None,
    window: tuple[str, str] | None = None,
    timeout: int = 60,
) -> QueryResult:
    """Agrège les logs Datadog sur `window` ou les `days` derniers jours. Renvoie un QueryResult, ne lève jamais."""
    return query.execute_datadog_query(
        search=search,
        caller=CallerType.APP,
        days=days,
        group_by=group_by,
        compute=compute,
        window=window,
        timeout=timeout,
    )


def count_datadog(
    search: str,
    days: int = 7,
    distinct: str | None = None,
    window: tuple[str, str] | None = None,
    timeout: int = 60,
) -> QueryResult:
    """Compte les événements Datadog, et la cardinalité de `distinct` s'il est donné. Ne lève jamais."""
    return query.execute_datadog_count(
        search=search, caller=CallerType.APP, days=days, distinct=distinct, window=window, timeout=timeout
    )


def sample_datadog(
    search: str,
    days: int = 7,
    limit: int = 100,
    window: tuple[str, str] | None = None,
    timeout: int = 60,
) -> QueryResult:
    """Renvoie jusqu'à `limit` événements Datadog bruts, du plus récent au plus ancien. Ne lève jamais."""
    return query.execute_datadog_events(
        search=search, caller=CallerType.APP, days=days, limit=limit, window=window, timeout=timeout
    )


def query_autometa_tables(sql: str, timeout: int = 60) -> QueryResult:
    """Interroge autometa_tables_db. Renvoie un QueryResult, ne lève jamais."""
    return query.execute_autometa_tables_query(sql=sql, caller=CallerType.APP, timeout=timeout)


def query_storage(sql: str, params: dict | None = None, timeout: int = 60) -> QueryResult:
    """Lit et écrit dans le schéma dashboard_storage. Renvoie un QueryResult, ne lève jamais."""
    return query.execute_dashboard_storage_query(sql=sql, caller=CallerType.APP, params=params, timeout=timeout)
