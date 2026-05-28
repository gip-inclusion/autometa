"""Run a harness eval benchmark against the S3 corpus and persist the result to S3."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from evals.metrics.gold_backed import build_gold_backed_metrics
from evals.metrics.gold_free import ALL_GOLD_FREE_METRICS
from lib import eval_corpus
from lib.harness_eval import run_benchmark


def cmd_benchmark(args: argparse.Namespace) -> None:
    if args.session_ids:
        sessions = [s for sid in args.session_ids if (s := eval_corpus.load_session(sid)) is not None]
    else:
        sessions = eval_corpus.load_all_sessions()

    if not sessions:
        print(json.dumps({"error": "No sessions loaded from S3"}))
        sys.exit(1)

    metrics = list(ALL_GOLD_FREE_METRICS)
    if not args.no_gold:
        gold_by_id = {gid: g for gid in eval_corpus.list_golds() if (g := eval_corpus.load_gold(gid)) is not None}
        metrics.extend(build_gold_backed_metrics(gold_by_id))

    result = run_benchmark(sessions, metrics, run_id=args.run_id)
    if not eval_corpus.persist_run(result):
        print(json.dumps({"error": "Failed to persist run to S3"}))
        sys.exit(2)

    print(json.dumps({
        "run_id": result.run_id,
        "sessions": len(result.session_results),
        "aggregate_scores": result.aggregate_scores,
        "s3_key": f"results/{result.run_id}.json",
    }, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run harness eval benchmark")
    sub = parser.add_subparsers(dest="command", required=True)

    bench = sub.add_parser("benchmark", help="Run benchmark on the S3 corpus")
    bench.add_argument("--session-ids", nargs="+", help="Specific session IDs to evaluate")
    bench.add_argument("--run-id", default=None, help="Custom run ID")
    bench.add_argument("--no-gold", action="store_true", help="Skip gold-backed metrics")

    args = parser.parse_args()
    {"benchmark": cmd_benchmark}[args.command](args)


if __name__ == "__main__":
    main()
