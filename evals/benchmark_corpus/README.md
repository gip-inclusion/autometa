# Benchmark corpus

The harness eval corpus lives in **S3, not git**. This keeps real conversation data out of the open-source repo and makes the eval suite trivially deploy-agnostic — any autometa fork brings its own corpus.

## S3 layout

```
s3://<S3_BUCKET>/<EVAL_CORPUS_S3_PREFIX>
├── sessions/<session-id>.jsonl   # Claude Code session transcripts
├── gold/<short-id>.json          # Gold annotations (format: see GOLD_FORMAT.md)
└── results/<run-id>.json         # Persisted RunResult per benchmark execution
```

`EVAL_CORPUS_S3_PREFIX` defaults to `eval_corpus/`. Configurable via env var.

## Bootstrap a corpus

1. Collect Claude Code sessions (typically from your `sessions/` S3 backup) into a local directory.
2. **Pseudonymize** with `scripts/pseudonymize.py` (emails, phones, internal IDs).
3. Push to S3 with the sync script:
   ```bash
   python -m skills.harness_eval.scripts.sync push --local-dir /path/to/sessions --subpath sessions/
   python -m skills.harness_eval.scripts.sync push --local-dir /path/to/gold     --subpath gold/
   ```

## Pull for local work

```bash
python -m skills.harness_eval.scripts.sync pull --local-dir /tmp/eval_corpus
```

## Run

```bash
python -m skills.harness_eval.scripts.run benchmark
```

Then view results at `/harness-eval` in the autometa web UI (admin only).
