"""Query execution with observability logging."""

import hashlib
import logging
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Optional

import httpx
from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode
from sqlalchemy.exc import ProgrammingError

from web import config

from . import notion
from .airtable import AirtableClient
from .data_inclusion import execute_sql as _di_execute_sql
from .datadog import DatadogClient, DatadogError, by_count, scoped_to_service
from .datadog import window as rolling_window
from .matomo import MatomoAPI, MatomoError
from .metabase import MetabaseAPI, MetabaseError
from .pg import execute_sql as _pg_execute_sql
from .sources import get_matomo, get_metabase, get_zendesk
from .tally import TallyClient

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
        # Why: les lignes suivantes d'une erreur Postgres (« Failing row contains… ») recopient
        # les valeurs de la requête, données personnelles comprises.
        headline = result.error.partition("\n")[0]
        span.set_status(Status(StatusCode.ERROR, headline[:200]))
        span.set_attribute("error.message", headline[:500])


class CallerType(str, Enum):
    """Type of caller making the query."""

    AGENT = "agent"
    APP = "app"
    CRON = "cron"


@dataclass
class QueryResult:
    """Result of a query execution."""

    success: bool
    data: Any
    error: Optional[str] = None
    execution_time_ms: int = 0
    invalid_request: bool = False


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
                success=False,
                data=None,
                error=str(e),
                execution_time_ms=int((time.time() - start) * 1000),
                # Why: SQL invalide, table ou schéma absent, droit manquant — la faute est à la requête, pas à la source.
                invalid_request=isinstance(e, ProgrammingError),
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
            log_attrs["query.error.message"] = result.error.partition("\n")[0][:200]
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
    params: Optional[dict[str, int | str]] = None,
) -> QueryResult:
    """Execute a Metabase query (sql+database_id or card_id), `{{name}}` bound from params. Never raises."""
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
            return _wrap_columns_rows(api.execute_sql(sql, timeout=timeout, params=params))
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
            _pg_execute_sql(
                database_url=config.AUTOMETA_TABLES_DATABASE_URL,
                sql=sql,
                source="autometa_tables_db",
                timeout=timeout,
            )
        )

    # Why: psycopg2 can raise a wide variety of errors; caller checks result.success.
    return _run_traced_query("autometa_tables.query", attrs, _do)


def execute_dora_staging_query(
    sql: str,
    caller: CallerType,
    timeout: int = 60,
) -> QueryResult:
    """Execute a SQL query on the Dora staging database (read-only). Returns QueryResult, never raises."""
    from web import config

    attrs = {
        "db.system": "postgresql",
        "db.name": "dora_staging",
        "caller": caller.value,
        "db.statement.hash": _sql_hash(sql),
    }

    def _do():
        if not config.DORA_STAGING_DB_URL:
            raise ValueError("DORA_STAGING_DB_URL is not configured")
        return _wrap_columns_rows(
            _pg_execute_sql(
                database_url=config.DORA_STAGING_DB_URL,
                sql=sql,
                source="dora_staging",
                instance="staging",
                timeout=timeout,
            )
        )

    # Why: psycopg2 can raise a wide variety of errors; caller checks result.success.
    return _run_traced_query("dora_staging.query", attrs, _do)


def execute_appli_monrecap_query(
    sql: str,
    caller: CallerType,
    params: Optional[dict] = None,
    timeout: int = 60,
) -> QueryResult:
    """Execute SQL on the Mon Récap application database (read/write, explicit calls only). Never raises."""
    from web import config

    attrs = {
        "db.system": "postgresql",
        "db.name": "appli_monrecap",
        "caller": caller.value,
        "db.statement.hash": _sql_hash(sql),
    }

    def _do():
        if not config.MONRECAP_APPLI_DB_URL:
            raise ValueError("MONRECAP_APPLI_DB_URL is not configured")
        return _wrap_columns_rows(
            _pg_execute_sql(
                database_url=config.MONRECAP_APPLI_DB_URL,
                sql=sql,
                source="appli_monrecap",
                params=params,
                write=True,
                timeout=timeout,
            )
        )

    # Why: psycopg2 can raise a wide variety of errors; caller checks result.success.
    return _run_traced_query("appli_monrecap.query", attrs, _do)


def execute_dashboard_storage_query(
    sql: str,
    caller: CallerType,
    params: Optional[dict] = None,
    timeout: int = 60,
) -> QueryResult:
    """Execute SQL on the dashboard_storage schema of the app database. Returns QueryResult, never raises."""
    from web import config

    attrs = {
        "db.system": "postgresql",
        "db.name": "dashboard_storage",
        "caller": caller.value,
        "db.statement.hash": _sql_hash(sql),
    }

    def _do():
        if not config.DASHBOARD_STORAGE_DB_URL:
            raise ValueError("DASHBOARD_STORAGE_DB_URL is not configured")
        return _wrap_columns_rows(
            _pg_execute_sql(
                database_url=config.DASHBOARD_STORAGE_DB_URL,
                sql=sql,
                source="dashboard_storage",
                params=params,
                write=True,
                timeout=timeout,
            )
        )

    # Why: SQLAlchemy/psycopg2 can raise a wide variety of errors; caller checks result.success.
    return _run_traced_query("dashboard_storage.query", attrs, _do)


def _run_datadog(
    span_name: str,
    search: str,
    caller: CallerType,
    days: int,
    window: Optional[tuple[str, str]],
    timeout: int,
    fn: Callable[[DatadogClient, str, str], Any],
    extra_attrs: Optional[dict] = None,
) -> QueryResult:
    attrs = {
        "db.system": "datadog",
        "caller": caller.value,
        "datadog.window": str(window) if window else f"{days}d",
        "db.statement.hash": _sql_hash(str(search)),
        **(extra_attrs or {}),
    }

    def _do():
        if not isinstance(search, str):
            raise DatadogError(f"search doit être une chaîne, pas {type(search).__name__}")
        frm, to = window or rolling_window(days)
        with DatadogClient(timeout=timeout) as client:
            return fn(client, frm, to)

    # Why: a 200 with an unexpected body raises KeyError/JSONDecodeError, not DatadogError; caller checks result.success.
    return _run_traced_query(span_name, attrs, _do)


def execute_datadog_query(
    search: str,
    caller: CallerType,
    days: int = 7,
    group_by: Optional[list[str | dict]] = None,
    compute: Optional[list[dict]] = None,
    window: Optional[tuple[str, str]] = None,
    timeout: int = 60,
) -> QueryResult:
    """Aggregate Datadog logs over `window` or the last `days` days. Returns QueryResult, never raises."""

    def aggregate(client: DatadogClient, frm: str, to: str) -> list[dict]:
        facets = [by_count(facet) if isinstance(facet, str) else facet for facet in group_by or []]
        return client.aggregate(search, frm, to, group_by=facets or None, compute=compute)

    return _run_datadog(
        "datadog.query", search=search, caller=caller, days=days, window=window, timeout=timeout, fn=aggregate
    )


def execute_datadog_count(
    search: str,
    caller: CallerType,
    days: int = 7,
    distinct: Optional[str] = None,
    window: Optional[tuple[str, str]] = None,
    timeout: int = 60,
) -> QueryResult:
    """Count Datadog log events, plus a facet's cardinality when `distinct` is given. Never raises."""
    return _run_datadog(
        "datadog.count",
        search=search,
        caller=caller,
        days=days,
        window=window,
        timeout=timeout,
        fn=lambda client, frm, to: client.count(search, frm, to, distinct=distinct),
    )


def execute_datadog_events(
    service: str,
    caller: CallerType,
    search: str = "",
    days: int = 7,
    limit: int = 100,
    window: Optional[tuple[str, str]] = None,
    timeout: int = 60,
) -> QueryResult:
    """Fetch up to `limit` raw Datadog log events of one service, newest first. Never raises."""

    # Why: raw events carry PII (URLs, user ids, headers) and a dashboard may publish what it reads,
    # so a sample is confined to one named service and bounded well under the cron time budget.
    def sample(client: DatadogClient, frm: str, to: str) -> list[dict]:
        query = scoped_to_service(service, search)
        if not isinstance(limit, int) or limit > 10_000:
            raise DatadogError(f"limit {limit!r} invalide : un entier, 10000 événements au plus")
        return list(client.iter_events(query, frm, to, max_events=limit, sort="-timestamp"))

    return _run_datadog(
        "datadog.events",
        search=search,
        caller=caller,
        days=days,
        window=window,
        timeout=timeout,
        fn=sample,
        extra_attrs={"datadog.service": str(service)},
    )


def execute_airtable_query(
    base_id: str,
    table: str,
    caller: CallerType,
    view: Optional[str] = None,
    fields: Optional[list[str]] = None,
    formula: Optional[str] = None,
    timeout: int = 60,
) -> QueryResult:
    """Read the records of an Airtable table or view. Returns QueryResult, never raises."""
    attrs = {
        "db.system": "airtable",
        "caller": caller.value,
        "airtable.base": str(base_id),
        "airtable.table": str(table),
    }

    def _do():
        with AirtableClient(timeout=timeout) as client:
            return client.list_records(base_id, table, view=view, fields=fields, formula=formula)

    # Why: a 200 with an unexpected body raises JSONDecodeError/AttributeError, not AirtableError; caller checks result.success.
    return _run_traced_query("airtable.query", attrs, _do)


def execute_github_query(
    path: str, caller: CallerType, params: Optional[dict] = None, timeout: int = 30
) -> QueryResult:
    """GET on the GitHub REST API (read-only), gip-inclusion repositories only. Returns QueryResult, never raises."""
    path = str(path).lstrip("/")
    # Why: the app token can read every repository it sees, private ones included — a dashboard may publish what it reads.
    if not path.startswith("repos/gip-inclusion/") or ".." in path:
        return QueryResult(
            success=False,
            data=None,
            error=f"{path} : seuls les chemins repos/gip-inclusion/… sont permis",
            invalid_request=True,
        )
    attrs = {"db.system": "github", "caller": caller.value, "github.path": path}

    def _do():
        headers = {"Accept": "application/vnd.github+json"}
        if config.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
        response = httpx.get(f"https://api.github.com/{path}", params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()

    return _run_traced_query("github.query", attrs, _do)


def execute_notion_query(
    database_id: str, caller: CallerType, filter: Optional[dict] = None, sorts: Optional[list[dict]] = None
) -> QueryResult:
    """All pages of a Notion database (read-only). Returns QueryResult, never raises."""
    attrs = {"db.system": "notion", "caller": caller.value, "notion.database": str(database_id)}
    return _run_traced_query(
        "notion.query", attrs, lambda: notion.query_database(database_id, filter=filter, sorts=sorts)
    )


def execute_tally_query(
    form_id: str, caller: CallerType, filter: Optional[str] = None, timeout: int = 30
) -> QueryResult:
    """Questions and submissions of a Tally form (read-only). Returns QueryResult, never raises."""
    attrs = {"db.system": "tally", "caller": caller.value, "tally.form": str(form_id)}

    def _do():
        with TallyClient(timeout=timeout) as client:
            return {
                "questions": client.list_questions(form_id).get("questions", []),
                "submissions": list(client.iter_submissions(form_id, filter=filter)),
            }

    return _run_traced_query("tally.query", attrs, _do)


def execute_zendesk_search(
    query: str,
    caller: CallerType,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
    max_results: int = 100,
) -> QueryResult:
    """Zendesk ticket search, subjects redacted. Returns QueryResult, never raises."""
    attrs = {"db.system": "zendesk", "caller": caller.value, "zendesk.path": "search.json"}

    def _do():
        with get_zendesk() as client:
            tickets = client.search_tickets(query, sort_by=sort_by, sort_order=sort_order, max_results=max_results)
            return [asdict(ticket) for ticket in tickets]

    return _run_traced_query("zendesk.search", attrs, _do)


def execute_zendesk_view_counts(view_ids: list[int], caller: CallerType) -> QueryResult:
    """Ticket count of each Zendesk view. Returns QueryResult, never raises."""
    attrs = {"db.system": "zendesk", "caller": caller.value, "zendesk.path": "views/count_many"}

    def _do():
        with get_zendesk() as client:
            return client.count_views(view_ids)

    return _run_traced_query("zendesk.view_counts", attrs, _do)


def execute_zendesk_view_dates(view_id: int, caller: CallerType) -> QueryResult:
    """Creation dates of the tickets in a Zendesk view. Returns QueryResult, never raises."""
    attrs = {"db.system": "zendesk", "caller": caller.value, "zendesk.path": f"views/{view_id}/tickets"}

    def _do():
        with get_zendesk() as client:
            return client.view_ticket_dates(view_id)

    return _run_traced_query("zendesk.view_dates", attrs, _do)


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
    if source in ("dashboard_storage", "matometa_db"):  # matometa_db : alias legacy utilisé par des app.js déployés
        return execute_dashboard_storage_query(sql=sql or "", caller=caller, params=params, timeout=timeout)
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
    if source == "appli_monrecap":
        return execute_appli_monrecap_query(sql=sql or "", caller=caller, params=params, timeout=timeout)
    return QueryResult(
        success=False,
        data=None,
        error=f"Unknown source: {source}. Use 'metabase', 'matomo', 'data_inclusion', 'autometa_tables_db', 'dashboard_storage', or 'appli_monrecap'.",
        invalid_request=True,
    )
