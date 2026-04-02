"""Query execution with observability logging."""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from .data_inclusion import execute_sql as _di_execute_sql
from .matomo import MatomoAPI, MatomoError
from .metabase import MetabaseAPI, MetabaseError
from .sources import get_matomo, get_metabase

__all__ = ["MatomoAPI", "MatomoError", "MetabaseAPI", "MetabaseError", "get_matomo", "get_metabase"]


class CallerType(str, Enum):
    """Type of caller making the query."""

    AGENT = "agent"
    APP = "app"


@dataclass
class QueryResult:
    """Result of a query execution."""

    success: bool
    data: Any
    error: Optional[str] = None
    execution_time_ms: int = 0


def execute_metabase_query(
    instance: str,
    caller: CallerType,
    sql: Optional[str] = None,
    database_id: Optional[int] = None,
    card_id: Optional[int] = None,
    timeout: int = 60,
) -> QueryResult:
    """
    Execute a Metabase query with logging.

    Either sql+database_id or card_id must be provided.
    Returns QueryResult (never raises).
    """
    start_time = time.time()

    try:
        # Get API client (logging is built into the class)
        api = get_metabase(instance, database_id=database_id)
        # Override caller for logging consistency
        api.caller = caller.value

        if sql:
            result = api.execute_sql(sql, timeout=timeout)
            data = {
                "columns": result.columns,
                "rows": result.rows,
                "row_count": result.row_count,
            }
        elif card_id is not None:
            result = api.execute_card(card_id, timeout=timeout)
            data = {
                "columns": result.columns,
                "rows": result.rows,
                "row_count": result.row_count,
            }
        else:
            raise ValueError("Either sql+database_id or card_id must be provided")

        execution_time_ms = int((time.time() - start_time) * 1000)
        return QueryResult(success=True, data=data, execution_time_ms=execution_time_ms)

    except (MetabaseError, ValueError) as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return QueryResult(success=False, data=None, error=str(e), execution_time_ms=execution_time_ms)


def execute_matomo_query(
    instance: str,
    caller: CallerType,
    method: str = "",
    params: Optional[dict] = None,
    timeout: int = 180,
) -> QueryResult:
    """
    Execute a Matomo API query with logging.
    Returns QueryResult (never raises).
    """
    start_time = time.time()
    params = params or {}

    try:
        # Get API client (logging is built into the class)
        api = get_matomo(instance)
        # Override caller for logging consistency
        api.caller = caller.value

        data = api.request(method, timeout=timeout, **params)

        execution_time_ms = int((time.time() - start_time) * 1000)
        return QueryResult(success=True, data=data, execution_time_ms=execution_time_ms)

    except MatomoError as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return QueryResult(success=False, data=None, error=str(e), execution_time_ms=execution_time_ms)


def execute_data_inclusion_query(
    sql: str,
    caller: CallerType,
    timeout: int = 60,
) -> QueryResult:
    """Execute a SQL query on the data·inclusion datawarehouse. Returns QueryResult (never raises)."""
    from web import config

    start_time = time.time()
    try:
        result = _di_execute_sql(
            database_url=config.DATA_INCLUSION_DATABASE_URL,
            ssh_host=config.DATA_INCLUSION_SSH_HOST,
            ssh_user=config.DATA_INCLUSION_SSH_USER,
            ssh_key=config.DATA_INCLUSION_SSH_KEY,
            ssh_key_passphrase=config.DATA_INCLUSION_SSH_KEY_PASSPHRASE,
            sql=sql,
        )
        data = {
            "columns": result.columns,
            "rows": result.rows,
            "row_count": result.row_count,
        }
        execution_time_ms = int((time.time() - start_time) * 1000)
        return QueryResult(success=True, data=data, execution_time_ms=execution_time_ms)
    # Why: query executor must return QueryResult, not raise — caller checks result.success.
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return QueryResult(success=False, data=None, error=str(e), execution_time_ms=execution_time_ms)


def execute_query(
    source: str,
    instance: str,
    caller: CallerType,
    # Metabase params
    sql: Optional[str] = None,
    database_id: Optional[int] = None,
    card_id: Optional[int] = None,
    # Matomo params
    method: Optional[str] = None,
    params: Optional[dict] = None,
    # Common
    timeout: int = 60,
) -> QueryResult:
    if source == "metabase":
        return execute_metabase_query(
            instance=instance,
            caller=caller,
            sql=sql,
            database_id=database_id,
            card_id=card_id,
            timeout=timeout,
        )
    if source == "matomo":
        return execute_matomo_query(
            instance=instance,
            caller=caller,
            method=method or "",
            params=params,
            timeout=timeout,
        )
    if source == "data_inclusion":
        return execute_data_inclusion_query(
            sql=sql or "",
            caller=caller,
            timeout=timeout,
        )
    return QueryResult(
        success=False,
        data=None,
        error=f"Unknown source: {source}. Use 'metabase', 'matomo', or 'data_inclusion'.",
    )
