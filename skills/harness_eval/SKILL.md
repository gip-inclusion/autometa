---
name: harness_eval
description: Run harness evaluation benchmarks against the S3-backed session corpus and view results in /harness-eval
---

# Harness Eval

Evaluate the autometa harness (system prompt, settings, skills, hooks) against a corpus of real Claude Code sessions, scored with gold-free automated metrics.

## Where data lives

| What | Where |
|------|-------|
| Session JSONLs (corpus) | `s3://<S3_BUCKET>/<EVAL_CORPUS_S3_PREFIX>sessions/*.jsonl` |
| Gold annotations | `s3://<S3_BUCKET>/<EVAL_CORPUS_S3_PREFIX>gold/*.json` |
| Run results | `s3://<S3_BUCKET>/<EVAL_CORPUS_S3_PREFIX>results/*.json` |
| Metric specs | `evals/metrics/SOTA_METRICS.md`, `evals/metrics/APP_METRICS.md` |
| Gold format spec | `evals/benchmark_corpus/GOLD_FORMAT.md` |

`EVAL_CORPUS_S3_PREFIX` defaults to `eval_corpus/`. Each deployment brings its own corpus — nothing is shipped in git.

## CLI

```bash
# Run benchmark on full S3 corpus, persist result to S3
python -m skills.harness_eval.scripts.run benchmark

# Run on a subset (specific session IDs)
python -m skills.harness_eval.scripts.run benchmark --session-ids 0108b9c9 0383d991

# Push a local corpus directory to S3 (one-time bootstrap)
python -m skills.harness_eval.scripts.sync push --local-dir /path/to/corpus

# Pull S3 corpus to local dir
python -m skills.harness_eval.scripts.sync pull --local-dir /path/to/local
```

## Web UI

Admin-only (uses `ADMIN_USERS`):
- `/harness-eval` — list runs
- `/harness-eval/runs/<run-id>` — single run detail
- `/harness-eval/diff?baseline=<id>&variant=<id>` — diff two runs

## Gold-free metrics

7 metrics scored without annotation:
`sql_syntactic_validity`, `correction_rate`, `tool_chain_length`, `knowledge_utilization`, `hallucination_signals`, `token_efficiency`, `sql_presence`.

Add custom metrics in `evals/metrics/gold_free.py` and append to `ALL_GOLD_FREE_METRICS`.
