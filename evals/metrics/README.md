# Metrics

Two metric families:

- **Gold-free** (`gold_free.py`) — no human annotation required, score from session structure alone.
- **Gold-backed** (to add as gold annotations land) — compare agent output to a gold answer.

## Gold-free metrics

| Metric | What | Score range |
|--------|------|-------------|
| `sql_syntactic_validity` | Fraction of SQL blocks that parse (sqlglot or fallback) | 0–1 |
| `correction_rate` | 1 − share of user turns hitting correction keywords | 0–1 |
| `tool_chain_length` | `1 / (1 + max_chain_per_turn / 10)` | 0–1 |
| `knowledge_utilization` | 1 if a `knowledge/` Read precedes first API call, else 0 | 0 or 1 |
| `hallucination_signals` | Penalize references to unknown Matomo site IDs | 0–1 |
| `token_efficiency` | Composite of output/total ratio and cache hit rate | 0–1 |
| `sql_presence` | Data questions should produce SQL | 0 or 1 |

## Adding a metric

```python
def metric_my_new_check(session: Session) -> MetricResult:
    return MetricResult(name="my_new_check", score=..., details={...})

ALL_GOLD_FREE_METRICS.append(metric_my_new_check)
```

The runner catches per-metric exceptions so one broken metric won't abort a run.

## Specs

See `SOTA_METRICS.md` (literature review: BLEU, ROUGE, BERTScore, LLM-judge, pass@k) and `APP_METRICS.md` (autometa-specific: SQL quality, proxy coherence, skill routing, hallucination signals) for the full taxonomy and prioritization rationale.
