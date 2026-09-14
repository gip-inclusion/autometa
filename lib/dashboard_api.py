"""Façade des tableaux de bord — seul module de ce dépôt qu'un TDB a le droit d'importer."""

# Les tableaux de bord vivent sur S3, hors du dépôt : aucun diff ne les voit, donc aucun refactor
# ne peut mesurer ce qu'il casse chez eux. Plutôt que de courir après les cassures, on réduit la
# surface où elles peuvent se produire — cette façade est un contrat, ses tests en sont la preuve.

from lib import query, variants
from lib.facade_imports import APPLICATION_PACKAGES, FACADE, facade_violations
from lib.query import CallerType, QueryResult
from web import config

__all__ = [
    "APPLICATION_PACKAGES",
    "FACADE",
    "VERSION",
    "QueryResult",
    "facade_violations",
    "list_variants",
    "query_autometa_tables",
    "query_data_inclusion",
    "query_matomo",
    "query_metabase",
    "query_storage",
]

VERSION = 2


def list_variants(slug: str | None = None) -> list[dict]:
    """Déclinaisons déclarées du tableau de bord dont le cron tourne : clé, libellé, jeton, chemin."""
    slug = slug or config.dashboard_slug()
    if slug is None:
        raise RuntimeError("AUTOMETA_DASHBOARD_SLUG absent : le cron ne sait pas pour quel tableau de bord il tourne")
    return variants.list_variants(slug)


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
