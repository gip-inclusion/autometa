"""Query execution with observability logging."""

import hashlib
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

from .autometa_tables_db import execute_sql as _atdb_execute_sql
from .data_inclusion import execute_sql as _di_execute_sql
from .matomo import MatomoAPI, MatomoError
from .metabase import MetabaseAPI, MetabaseError
from .sources import get_matomo, get_metabase

__all__ = ["MatomoAPI", "MatomoError", "MetabaseAPI", "MetabaseError", "get_matomo", "get_metabase"]

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


def _sql_hash(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]


def _row_count(data: Any) -> Optional[int]:
    if isinstance(data, dict) and "row_count" in data:
        return data["row_count"]
    if isinstance(data, list):
        return len(data)
    return None


def _record_result(span: Span, result: "QueryResult") -> None:
    span.set_attribute("result.success", result.success)
    row_count = _row_count(result.data)
    if row_count is not None:
        span.set_attribute("result.row_count", row_count)
    if result.error:
        span.set_status(Status(StatusCode.ERROR), result.error[:200])
        span.set_attribute("error.message", result.error[:500])


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


def _run_traced_query(
    span_name: str,
    attrs: dict,
    fn: Callable[[], Any],
    *,
    catches: tuple[type[BaseException], ...] = (Exception,),
) -> QueryResult:
    """Run fn inside a traced span, normalising success/error into QueryResult."""
    start = time.time()
    with tracer.start_as_current_span(span_name, attributes=attrs) as span:
        try:
            data = fn()
            result = QueryResult(success=True, data=data, execution_time_ms=int((time.time() - start) * 1000))
        except catches as e:
            result = QueryResult(
                success=False, data=None, error=str(e), execution_time_ms=int((time.time() - start) * 1000)
            )
        _record_result(span, result)
        log_attrs: dict[str, Any] = {
            **attrs,
            "query.duration": result.execution_time_ms,
            "query.success": result.success,
        }
        row_count = _row_count(result.data)
        if row_count is not None:
            log_attrs["query.row_count"] = row_count
        if result.error:
            log_attrs["query.error.message"] = result.error[:200]
        logger.info(span_name, extra=log_attrs)
        return result


def _wrap_columns_rows(inner) -> dict:
    return {"columns": inner.columns, "rows": inner.rows, "row_count": inner.row_count}


def execute_metabase_query(
    instance: str,
    caller: CallerType,
    sql: Optional[str] = None,
    database_id: Optional[int] = None,
    card_id: Optional[int] = None,
    timeout: int = 60,
) -> QueryResult:
    """Execute a Metabase query (sql+database_id or card_id). Returns QueryResult, never raises."""
    attrs: dict[str, Any] = {
        "db.system": "metabase",
        "metabase.instance": instance,
        "metabase.caller": caller.value,
    }
    if card_id is not None:
        attrs["metabase.card_id"] = card_id
    if sql:
        attrs["db.statement.hash"] = _sql_hash(sql)

    def _do():
        api = get_metabase(instance, database_id=database_id)
        api.caller = caller.value
        if sql:
            return _wrap_columns_rows(api.execute_sql(sql, timeout=timeout))
        if card_id is not None:
            return _wrap_columns_rows(api.execute_card(card_id, timeout=timeout))
        raise ValueError("Either sql+database_id or card_id must be provided")

    return _run_traced_query("metabase.query", attrs, _do, catches=(MetabaseError, ValueError))


def list_metabase_models(
    instance: str,
    caller: CallerType,
    timeout: int = 30,
) -> QueryResult:
    """List all model-type cards on a Metabase instance. Returns QueryResult, never raises."""
    attrs = {"db.system": "metabase", "metabase.instance": instance, "metabase.caller": caller.value}

    def _do():
        api = get_metabase(instance)
        api.caller = caller.value
        return api.list_models()

    return _run_traced_query("metabase.list_models", attrs, _do, catches=(MetabaseError, ValueError))


def execute_matomo_query(
    instance: str,
    caller: CallerType,
    method: str = "",
    params: Optional[dict] = None,
    timeout: int = 180,
) -> QueryResult:
    """Execute a Matomo API query. Returns QueryResult, never raises."""
    attrs = {
        "db.system": "matomo",
        "matomo.instance": instance,
        "matomo.caller": caller.value,
        "matomo.method": method,
    }
    request_params = params or {}

    def _do():
        api = get_matomo(instance)
        api.caller = caller.value
        return api.request(method, timeout=timeout, **request_params)

    return _run_traced_query("matomo.query", attrs, _do, catches=(MatomoError,))


def execute_data_inclusion_query(
    sql: str,
    caller: CallerType,
    timeout: int = 60,
) -> QueryResult:
    """Execute a SQL query on the data·inclusion datawarehouse. Returns QueryResult, never raises."""
    from web import config

    attrs = {"db.system": "data_inclusion", "caller": caller.value, "db.statement.hash": _sql_hash(sql)}

    def _do():
        return _wrap_columns_rows(
            _di_execute_sql(
                database_url=config.DATA_INCLUSION_DATABASE_URL,
                ssh_host=config.DATA_INCLUSION_SSH_HOST,
                ssh_user=config.DATA_INCLUSION_SSH_USER,
                ssh_key=config.DATA_INCLUSION_SSH_KEY,
                ssh_key_passphrase=config.DATA_INCLUSION_SSH_KEY_PASSPHRASE,
                sql=sql,
                timeout=timeout,
            )
        )

    # Why: SSH tunnel + psycopg2 can raise a wide variety of errors; caller checks result.success.
    return _run_traced_query("data_inclusion.query", attrs, _do)


def execute_autometa_tables_query(
    sql: str,
    caller: CallerType,
    timeout: int = 60,
) -> QueryResult:
    """Execute a SQL query on autometa_tables_db. Returns QueryResult, never raises."""
    from web import config

    attrs = {
        "db.system": "postgresql",
        "db.name": "autometa_tables_db",
        "caller": caller.value,
        "db.statement.hash": _sql_hash(sql),
    }

    def _do():
        return _wrap_columns_rows(
            _atdb_execute_sql(
                database_url=config.AUTOMETA_TABLES_DATABASE_URL,
                sql=sql,
                timeout=timeout,
            )
        )

    # Why: psycopg2 can raise a wide variety of errors; caller checks result.success.
    return _run_traced_query("autometa_tables.query", attrs, _do)


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
    if source == "autometa_tables_db":
        return execute_autometa_tables_query(
            sql=sql or "",
            caller=caller,
            timeout=timeout,
        )
    return QueryResult(
        success=False,
        data=None,
        error=f"Unknown source: {source}. Use 'metabase', 'matomo', 'data_inclusion', or 'autometa_tables_db'.",
    )
