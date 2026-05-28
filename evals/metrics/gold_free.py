"""Metrics that operate on a parsed Session without requiring gold annotations."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from lib.harness_eval import MetricResult

if TYPE_CHECKING:
    from lib.harness_eval import Session

try:
    import sqlglot
    import sqlglot.errors as _sqlglot_errors
except ImportError:  # Why: sqlglot is optional — fall back to a basic balanced-parens check.
    sqlglot = None  # type: ignore[assignment]
    _sqlglot_errors = None  # type: ignore[assignment]

CORRECTION_KEYWORDS_FR = [
    "non,", "non.", "non ", "pas ça", "pas comme ça", "c'est pas",
    "incorrect", "faux", "erreur", "tu te trompes",
    "essaie autrement", "recommence", "refais",
    "j'ai dit", "je voulais", "ce n'est pas ce que",
    "plutôt", "en fait,", "pas exactement",
]

KNOWN_MATOMO_SITE_IDS = {117, 136, 146, 206, 211, 212, 214, 217}

_SITE_ID_RE = re.compile(r"idSite\s*=\s*(\d+)")
_DATA_KEYWORDS = ("données", "statistiques", "combien", "requête", "sql", "table", "base")


def _basic_sql_check(sql: str) -> bool:
    upper = sql.upper().strip()
    if not any(upper.startswith(kw) for kw in ("SELECT", "WITH", "INSERT", "UPDATE", "DELETE", "EXPLAIN")):
        return False
    parens = 0
    for ch in sql:
        if ch == "(":
            parens += 1
        elif ch == ")":
            parens -= 1
        if parens < 0:
            return False
    return parens == 0


def metric_sql_syntactic_validity(session: Session) -> MetricResult:
    """Fraction of SQL statements that parse correctly."""
    all_sql = [sql for t in session.turns for sql in t.sql_statements]
    if not all_sql:
        return MetricResult(name="sql_syntactic_validity", score=1.0, details={"n_statements": 0, "note": "no SQL"})

    valid = 0
    invalid = []
    for sql in all_sql:
        if sqlglot is not None:
            try:
                sqlglot.parse(sql, dialect="postgres")
                valid += 1
            except _sqlglot_errors.ParseError:
                invalid.append(sql[:100])
        elif _basic_sql_check(sql):
            valid += 1
        else:
            invalid.append(sql[:100])

    return MetricResult(
        name="sql_syntactic_validity",
        score=valid / len(all_sql),
        details={"n_statements": len(all_sql), "n_valid": valid, "invalid_previews": invalid[:5]},
    )


def metric_correction_rate(session: Session) -> MetricResult:
    """1.0 minus the fraction of user turns containing correction keywords."""
    n = len(session.turns)
    if n == 0:
        return MetricResult(name="correction_rate", score=1.0, details={"n_corrections": 0, "n_user_turns": 0})

    indices = [
        t.index for t in session.turns
        if any(kw in t.user_text.lower() for kw in CORRECTION_KEYWORDS_FR)
    ]
    return MetricResult(
        name="correction_rate",
        score=max(0.0, 1.0 - len(indices) / n),
        details={
            "n_corrections": len(indices),
            "n_user_turns": n,
            "correction_indices": indices,
            "first_shot_success": not indices,
        },
    )


def metric_tool_chain_length(session: Session) -> MetricResult:
    """Inverse of max tool-chain length per turn (1/(1+max/10))."""
    if not session.turns:
        return MetricResult(name="tool_chain_length", score=1.0, details={"n_turns": 0})

    chain_lengths = [len(t.tool_calls) for t in session.turns]
    total = sum(chain_lengths)
    unique = sorted({tc.name for t in session.turns for tc in t.tool_calls})
    max_chain = max(chain_lengths)
    return MetricResult(
        name="tool_chain_length",
        score=1.0 / (1.0 + max_chain / 10.0),
        details={
            "total_tool_calls": total,
            "max_chain": max_chain,
            "mean_chain": round(total / len(session.turns), 2),
            "unique_tools": unique,
            "n_turns": len(session.turns),
        },
    )


def metric_knowledge_utilization(session: Session) -> MetricResult:
    """1.0 if any knowledge/ Read precedes the first API-style tool call; 0.0 otherwise."""
    api_tools = {"Bash", "Skill", "Task"}
    knowledge_reads: set[str] = set()
    api_before_knowledge = False
    saw_api = False

    for turn in session.turns:
        for tc in turn.tool_calls:
            if tc.name == "Read":
                target = tc.input.get("file_path", "") or tc.input.get("path", "")
                if "knowledge/" in target:
                    knowledge_reads.add(target)
            elif tc.name in api_tools and not saw_api:
                saw_api = True
                if not knowledge_reads:
                    api_before_knowledge = True

    if not saw_api:
        return MetricResult(name="knowledge_utilization", score=1.0, details={"note": "no API calls"})

    return MetricResult(
        name="knowledge_utilization",
        score=0.0 if api_before_knowledge else 1.0,
        details={
            "knowledge_reads_before_api": len(knowledge_reads),
            "api_called_before_knowledge": api_before_knowledge,
            "knowledge_files_read": sorted(knowledge_reads),
        },
    )


def metric_hallucination_signals(session: Session) -> MetricResult:
    """Detect references to Matomo site IDs not in the known set."""
    phantom: list[int] = []

    def scan(text: str) -> None:
        for m in _SITE_ID_RE.finditer(text):
            sid = int(m.group(1))
            if sid not in KNOWN_MATOMO_SITE_IDS and sid not in phantom:
                phantom.append(sid)

    for turn in session.turns:
        scan(turn.assistant_text)
        scan(turn.thinking)
        for sql in turn.sql_statements:
            scan(sql)

    score = 1.0 if not phantom else max(0.0, 1.0 - len(phantom) * 0.25)
    return MetricResult(
        name="hallucination_signals",
        score=score,
        details={"phantom_site_ids": phantom, "n_phantom": len(phantom)},
    )


def metric_token_efficiency(session: Session) -> MetricResult:
    """Composite of output ratio and cache hit rate."""
    total_in = session.total_input_tokens
    total_out = session.total_output_tokens
    total = total_in + total_out
    if total == 0:
        return MetricResult(name="token_efficiency", score=1.0, details={"note": "no tokens recorded"})

    cache_read = sum(t.cache_read_tokens for t in session.turns)
    cache_hit_rate = cache_read / total_in if total_in > 0 else 0.0
    output_ratio = total_out / total

    return MetricResult(
        name="token_efficiency",
        score=round(min(1.0, output_ratio * 3.0 + cache_hit_rate * 0.5), 4),
        details={
            "total_input": total_in,
            "total_output": total_out,
            "cache_read": cache_read,
            "cache_hit_rate": round(cache_hit_rate, 4),
            "output_ratio": round(output_ratio, 4),
        },
    )


def metric_sql_presence(session: Session) -> MetricResult:
    """Sessions whose user turns request data should produce SQL."""
    all_sql = [sql for t in session.turns for sql in t.sql_statements]
    user_text = " ".join(t.user_text.lower() for t in session.turns)
    asks_for_data = any(kw in user_text for kw in _DATA_KEYWORDS)

    if not asks_for_data:
        return MetricResult(name="sql_presence", score=1.0, details={"note": "no data request detected", "n_sql": len(all_sql)})

    return MetricResult(
        name="sql_presence",
        score=1.0 if all_sql else 0.0,
        details={"n_sql": len(all_sql), "asks_for_data": True},
    )


ALL_GOLD_FREE_METRICS = [
    metric_sql_syntactic_validity,
    metric_correction_rate,
    metric_tool_chain_length,
    metric_knowledge_utilization,
    metric_hallucination_signals,
    metric_token_efficiency,
    metric_sql_presence,
]
