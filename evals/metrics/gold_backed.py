"""Metrics that require gold annotations. Built as closures over a gold lookup dict."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lib.harness_eval import MetricResult

if TYPE_CHECKING:
    from lib.harness_eval import Gold, Session


def _gold_for(session: Session, gold_by_id: dict[str, Gold]) -> Gold | None:
    return gold_by_id.get(session.session_id[:8])


def make_metric_expected_skills_used(gold_by_id: dict[str, Gold]):
    """Fraction of gold.expected_skills actually invoked via tool_use Skill calls."""

    def metric_expected_skills_used(session: Session) -> MetricResult:
        gold = _gold_for(session, gold_by_id)
        if gold is None or not gold.expected_skills:
            return MetricResult(name="expected_skills_used", score=1.0, details={"note": "no gold"})

        invoked = {
            tc.input.get("skill", "")
            for t in session.turns
            for tc in t.tool_calls
            if tc.name == "Skill"
        }
        matched = set(gold.expected_skills) & invoked
        return MetricResult(
            name="expected_skills_used",
            score=len(matched) / len(gold.expected_skills),
            details={
                "expected": gold.expected_skills,
                "invoked": sorted(s for s in invoked if s),
                "matched": sorted(matched),
                "missing": sorted(set(gold.expected_skills) - invoked),
            },
        )

    return metric_expected_skills_used


def make_metric_overall_quality(gold_by_id: dict[str, Gold]):
    """Surface gold.overall_quality (1-5) normalized to 0-1 as a reference signal."""

    def metric_overall_quality(session: Session) -> MetricResult:
        gold = _gold_for(session, gold_by_id)
        if gold is None or gold.overall_quality is None:
            return MetricResult(name="overall_quality", score=1.0, details={"note": "no gold"})

        return MetricResult(
            name="overall_quality",
            score=gold.overall_quality / 5.0,
            details={
                "raw_score_1_to_5": gold.overall_quality,
                "difficulty": gold.difficulty,
                "tags": gold.tags,
            },
        )

    return metric_overall_quality


def build_gold_backed_metrics(gold_by_id: dict[str, Gold]) -> list:
    """Return the standard gold-backed metric list, bound to the given gold dict."""
    return [
        make_metric_expected_skills_used(gold_by_id),
        make_metric_overall_quality(gold_by_id),
    ]
