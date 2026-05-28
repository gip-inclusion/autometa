"""Harness evaluation infrastructure: session parsing, gold loading, metrics runner."""

import json
import logging
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """One tool invocation extracted from a session."""

    name: str
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class Turn:
    """One user→assistant exchange in a session."""

    index: int
    user_text: str
    assistant_text: str
    thinking: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    sql_statements: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    timestamp: str = ""


@dataclass
class Session:
    """Parsed session from a JSONL transcript."""

    session_id: str
    turns: list[Turn] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0


_SQL_BLOCK_RE = re.compile(r"```(?:sql)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
_SQL_KEYWORDS = ("SELECT", "INSERT", "UPDATE", "DELETE", "WITH", "EXPLAIN")


def _extract_sql(text: str) -> list[str]:
    out = []
    for m in _SQL_BLOCK_RE.finditer(text):
        sql = m.group(1).strip()
        if sql and any(kw in sql.upper() for kw in _SQL_KEYWORDS):
            out.append(sql)
    return out


def _parse_blocks(content: Any) -> tuple[str, str, list[ToolCall], list[str]]:
    text_parts: list[str] = []
    thinking_parts: list[str] = []
    tools: list[ToolCall] = []
    sql: list[str] = []

    if isinstance(content, str):
        text_parts.append(content)
        sql.extend(_extract_sql(content))
    elif isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "text":
                t = block.get("text", "")
                text_parts.append(t)
                sql.extend(_extract_sql(t))
            elif btype == "thinking":
                thinking_parts.append(block.get("thinking", ""))
            elif btype == "tool_use":
                tools.append(ToolCall(name=block.get("name", ""), input=block.get("input", {})))

    return "\n".join(text_parts), "\n".join(thinking_parts), tools, sql


def parse_session_jsonl(text: str, session_id: str) -> Session:
    """Parse a Claude Code session JSONL string into a Session."""
    user_messages: list[tuple[int, str, str]] = []
    assistant_blocks: list[dict] = []

    for raw in text.strip().split("\n"):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue

        msg_type = obj.get("type")
        message = obj.get("message", {})
        ts = obj.get("timestamp", "")

        if msg_type == "user" and isinstance(message, dict):
            content = message.get("content", "")
            if isinstance(content, str) and content.strip():
                user_messages.append((len(user_messages), content.strip(), ts))
            elif isinstance(content, list):
                txt = " ".join(
                    b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
                ).strip()
                if txt:
                    user_messages.append((len(user_messages), txt, ts))
        elif isinstance(message, dict) and message.get("role") == "assistant":
            assistant_blocks.append({
                "content": message.get("content", []),
                "usage": message.get("usage", {}),
                "timestamp": ts,
            })

    turns: list[Turn] = []
    asst_idx = 0

    for i, (idx, user_text, ts) in enumerate(user_messages):
        text_parts: list[str] = []
        thinking_parts: list[str] = []
        all_tools: list[ToolCall] = []
        all_sql: list[str] = []
        in_tok = out_tok = cache_tok = 0

        while asst_idx < len(assistant_blocks):
            block = assistant_blocks[asst_idx]
            next_ts = user_messages[i + 1][2] if i + 1 < len(user_messages) else None
            if next_ts and block["timestamp"] >= next_ts:
                break

            t, th, tools, sql = _parse_blocks(block["content"])
            if t:
                text_parts.append(t)
            if th:
                thinking_parts.append(th)
            all_tools.extend(tools)
            all_sql.extend(sql)

            usage = block.get("usage", {})
            in_tok += usage.get("input_tokens", 0)
            out_tok += usage.get("output_tokens", 0)
            cache_tok += usage.get("cache_read_input_tokens", 0)
            asst_idx += 1

        turns.append(
            Turn(
                index=idx,
                user_text=user_text,
                assistant_text="\n".join(text_parts),
                thinking="\n".join(thinking_parts),
                tool_calls=all_tools,
                sql_statements=all_sql,
                input_tokens=in_tok,
                output_tokens=out_tok,
                cache_read_tokens=cache_tok,
                timestamp=ts,
            )
        )

    total_in = sum(t.input_tokens for t in turns)
    total_out = sum(t.output_tokens for t in turns)
    return Session(session_id=session_id, turns=turns, total_input_tokens=total_in, total_output_tokens=total_out)


@dataclass
class GoldTurn:
    """Gold annotation for one turn."""

    turn_index: int
    gold_sql: str | None = None
    gold_sql_alternatives: list[str] = field(default_factory=list)
    gold_answer: str | None = None
    acceptable_alternatives: list[str] = field(default_factory=list)
    gold_action_trace: list[dict] | None = None
    expected_knowledge_reads: list[str] = field(default_factory=list)
    expected_source: str | None = None
    expected_instance: str | None = None
    is_correction: bool = False


@dataclass
class Gold:
    """Gold annotation for a full session."""

    session_id: str
    version: int = 0
    overall_quality: int | None = None
    correctness: int | None = None
    completeness: int | None = None
    difficulty: str = ""
    tags: list[str] = field(default_factory=list)
    expected_skills: list[str] = field(default_factory=list)
    turns: list[GoldTurn] = field(default_factory=list)


def parse_gold_json(text: str) -> Gold:
    """Parse a gold annotation JSON string."""
    data = json.loads(text)
    conv = data.get("conversation_level", {})
    turns = [
        GoldTurn(
            turn_index=t["turn_index"],
            gold_sql=t.get("gold_sql"),
            gold_sql_alternatives=t.get("gold_sql_alternatives", []),
            gold_answer=t.get("gold_answer"),
            acceptable_alternatives=t.get("acceptable_alternatives", []),
            gold_action_trace=t.get("gold_action_trace"),
            expected_knowledge_reads=t.get("expected_knowledge_reads", []),
            expected_source=t.get("expected_source"),
            expected_instance=t.get("expected_instance"),
            is_correction=t.get("is_correction", False),
        )
        for t in data.get("turns", [])
    ]
    return Gold(
        session_id=data["session_id"],
        version=data.get("version", 0),
        overall_quality=conv.get("overall_quality"),
        correctness=conv.get("correctness"),
        completeness=conv.get("completeness"),
        difficulty=conv.get("difficulty", ""),
        tags=conv.get("tags", []),
        expected_skills=conv.get("expected_skills", []),
        turns=turns,
    )


@dataclass
class MetricResult:
    """Result of a single metric evaluation on a session."""

    name: str
    score: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionResult:
    """Evaluation results for one session."""

    session_id: str
    metrics: list[MetricResult] = field(default_factory=list)
    error: str = ""


@dataclass
class RunResult:
    """Complete benchmark run result."""

    run_id: str
    timestamp: str
    session_results: list[SessionResult] = field(default_factory=list)
    aggregate_scores: dict[str, float] = field(default_factory=dict)


def _to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _to_dict(v) for k, v in obj.__dict__.items()}
    if isinstance(obj, list):
        return [_to_dict(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    return obj


def run_result_to_json(result: RunResult) -> str:
    """Serialize a RunResult to a JSON string."""
    return json.dumps(_to_dict(result), indent=2, ensure_ascii=False)


def run_result_from_json(text: str) -> RunResult:
    """Deserialize a RunResult from a JSON string."""
    data = json.loads(text)
    srs = []
    for sr in data.get("session_results", []):
        metrics = [MetricResult(**m) for m in sr.get("metrics", [])]
        srs.append(SessionResult(session_id=sr["session_id"], metrics=metrics, error=sr.get("error", "")))
    return RunResult(
        run_id=data["run_id"],
        timestamp=data["timestamp"],
        session_results=srs,
        aggregate_scores=data.get("aggregate_scores", {}),
    )


def run_metrics(session: Session, metric_fns: list) -> SessionResult:
    """Run all metric functions on a session, return SessionResult."""
    results = []
    for fn in metric_fns:
        try:
            r = fn(session)
            if isinstance(r, MetricResult):
                results.append(r)
            elif isinstance(r, list):
                results.extend(r)
        except Exception as exc:  # Why: one failing metric must not abort the entire session evaluation.
            logger.warning("Metric %s failed on session %s: %s", fn.__name__, session.session_id, exc)
            results.append(MetricResult(name=fn.__name__, score=0.0, details={"error": str(exc)}))
    return SessionResult(session_id=session.session_id, metrics=results)


def run_benchmark(sessions: list[Session], metric_fns: list, *, run_id: str | None = None) -> RunResult:
    """Run all metrics on all sessions, aggregate scores."""
    run_id = run_id or f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    session_results = [run_metrics(s, metric_fns) for s in sessions]

    sums: defaultdict[str, float] = defaultdict(float)
    counts: defaultdict[str, int] = defaultdict(int)
    for sr in session_results:
        for m in sr.metrics:
            sums[m.name] += m.score
            counts[m.name] += 1

    aggregate = {name: sums[name] / counts[name] for name in sorted(sums)}
    return RunResult(
        run_id=run_id,
        timestamp=datetime.now().isoformat(),
        session_results=session_results,
        aggregate_scores=aggregate,
    )


def diff_runs(baseline: RunResult, variant: RunResult) -> dict:
    """Compute a structured diff between two runs."""
    all_metrics = sorted(set(baseline.aggregate_scores) | set(variant.aggregate_scores))
    aggregate_diff = []
    for m in all_metrics:
        b = baseline.aggregate_scores.get(m, 0.0)
        v = variant.aggregate_scores.get(m, 0.0)
        aggregate_diff.append({"metric": m, "baseline": b, "variant": v, "delta": v - b})

    by_id_b = {sr.session_id: sr for sr in baseline.session_results}
    by_id_v = {sr.session_id: sr for sr in variant.session_results}
    per_session = []
    for sid in sorted(set(by_id_b) | set(by_id_v)):
        b_sr = by_id_b.get(sid)
        v_sr = by_id_v.get(sid)
        if not b_sr or not v_sr:
            continue
        b_m = {m.name: m.score for m in b_sr.metrics}
        v_m = {m.name: m.score for m in v_sr.metrics}
        changes = []
        for n in sorted(set(b_m) | set(v_m)):
            bv, vv = b_m.get(n, 0.0), v_m.get(n, 0.0)
            if bv != vv:
                changes.append({"metric": n, "baseline": bv, "variant": vv, "delta": vv - bv})
        if changes:
            per_session.append({"session_id": sid, "changes": changes})

    return {
        "baseline_run_id": baseline.run_id,
        "variant_run_id": variant.run_id,
        "aggregate": aggregate_diff,
        "per_session": per_session,
    }
