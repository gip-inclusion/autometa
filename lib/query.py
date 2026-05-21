"""Query execution with observability logging."""

import hashlib
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

from .autometa_tables_db import execute_sql as _atdb_execute_sql
from .data_inclusion import execute_sql as _di_execute_sql
from .matomo import MatomoAPI, MatomoError
from .metabase import MetabaseAPI, MetabaseError
from .sources import get_matomo, get_metabase

__all__ = ["MatomoAPI", "MatomoError", "MetabaseAPI", "MetabaseError", "get_matomo", "get_metabase"]

tracer = trace.get_tracer(__name__)


def _sql_hash(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]


def _record_result(span: Span, result: "QueryResult") -> None:
    span.set_attribute("result.success", result.success)
    row_count = _row_count(result.data)
    if row_count is not None:
        span.set_attribute("result.row_count", row_count)
    if result.error:
        span.set_status(Status(StatusCode.ERROR), result.error[:200])
        span.set_attribute("error.message", result.error[:500])


def _row_count(data: Any) -> Optional[int]:
    if isinstance(data, dict) and "row_count" in data:
        return data["row_count"]
    if isinstance(data, list):
        return len(data)
    return None


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

    start_time = time.time()
    with tracer.start_as_current_span("metabase.query", attributes=attrs) as span:
        try:
            api = get_metabase(instance, database_id=database_id)
            api.caller = caller.value
            if sql:
                inner = api.execute_sql(sql, timeout=timeout)
            elif card_id is not None:
                inner = api.execute_card(card_id, timeout=timeout)
            else:
                raise ValueError("Either sql+database_id or card_id must be provided")
            data = {"columns": inner.columns, "rows": inner.rows, "row_count": inner.row_count}
            result = QueryResult(success=True, data=data, execution_time_ms=int((time.time() - start_time) * 1000))
        except (MetabaseError, ValueError) as e:
            result = QueryResult(
                success=False, data=None, error=str(e), execution_time_ms=int((time.time() - start_time) * 1000)
            )
        _record_result(span, result)
        return result


def list_metabase_models(
    instance: str,
    caller: CallerType,
    timeout: int = 30,
) -> QueryResult:
    """List all model-type cards on a Metabase instance. Returns QueryResult, never raises."""
    attrs = {"db.system": "metabase", "metabase.instance": instance, "metabase.caller": caller.value}
    start_time = time.time()
    with tracer.start_as_current_span("metabase.list_models", attributes=attrs) as span:
        try:
            api = get_metabase(instance)
            api.caller = caller.value
            data = api.list_models()
            result = QueryResult(success=True, data=data, execution_time_ms=int((time.time() - start_time) * 1000))
        except (MetabaseError, ValueError) as e:
            result = QueryResult(
                success=False, data=None, error=str(e), execution_time_ms=int((time.time() - start_time) * 1000)
            )
        _record_result(span, result)
        return result


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
    params = params or {}
    start_time = time.time()
    with tracer.start_as_current_span("matomo.query", attributes=attrs) as span:
        try:
            api = get_matomo(instance)
            api.caller = caller.value
            data = api.request(method, timeout=timeout, **params)
            result = QueryResult(success=True, data=data, execution_time_ms=int((time.time() - start_time) * 1000))
        except MatomoError as e:
            result = QueryResult(
                success=False, data=None, error=str(e), execution_time_ms=int((time.time() - start_time) * 1000)
            )
        _record_result(span, result)
        return result


def execute_data_inclusion_query(
    sql: str,
    caller: CallerType,
    timeout: int = 60,
) -> QueryResult:
    """Execute a SQL query on the data·inclusion datawarehouse. Returns QueryResult, never raises."""
    from web import config

    attrs = {"db.system": "data_inclusion", "caller": caller.value, "db.statement.hash": _sql_hash(sql)}
    start_time = time.time()
    with tracer.start_as_current_span("data_inclusion.query", attributes=attrs) as span:
        try:
            inner = _di_execute_sql(
                database_url=config.DATA_INCLUSION_DATABASE_URL,
                ssh_host=config.DATA_INCLUSION_SSH_HOST,
                ssh_user=config.DATA_INCLUSION_SSH_USER,
                ssh_key=config.DATA_INCLUSION_SSH_KEY,
                ssh_key_passphrase=config.DATA_INCLUSION_SSH_KEY_PASSPHRASE,
                sql=sql,
                timeout=timeout,
            )
            data = {"columns": inner.columns, "rows": inner.rows, "row_count": inner.row_count}
            result = QueryResult(success=True, data=data, execution_time_ms=int((time.time() - start_time) * 1000))
        # Why: query executor must return QueryResult, not raise — caller checks result.success.
        except Exception as e:
            result = QueryResult(
                success=False, data=None, error=str(e), execution_time_ms=int((time.time() - start_time) * 1000)
            )
        _record_result(span, result)
        return result


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
    start_time = time.time()
    with tracer.start_as_current_span("autometa_tables.query", attributes=attrs) as span:
        try:
            inner = _atdb_execute_sql(
                database_url=config.AUTOMETA_TABLES_DATABASE_URL,
                sql=sql,
                timeout=timeout,
            )
            data = {"columns": inner.columns, "rows": inner.rows, "row_count": inner.row_count}
            result = QueryResult(success=True, data=data, execution_time_ms=int((time.time() - start_time) * 1000))
        # Why: query executor must return QueryResult, not raise — caller checks result.success.
        except Exception as e:
            result = QueryResult(
                success=False, data=None, error=str(e), execution_time_ms=int((time.time() - start_time) * 1000)
            )
        _record_result(span, result)
        return result


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
