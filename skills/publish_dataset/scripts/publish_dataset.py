"""CLI: run a SQL query against a PG source and publish the result as a job-accessible dataset."""

import argparse
import json
import sys

from lib import job_inputs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Publish a SQL query result as a job dataset (sqlite/jsonl/csv).")
    parser.add_argument("--slug", required=True, help="dataset name ([a-z0-9_-]); becomes the S3 filename")
    parser.add_argument("--source", required=True, choices=["autometa_tables_db", "data_inclusion"])
    parser.add_argument("--sql", required=True)
    parser.add_argument("--format", default="sqlite", choices=["sqlite", "jsonl", "csv"])
    args = parser.parse_args(argv)
    try:
        out = job_inputs.publish_query(args.slug, args.source, args.sql, fmt=args.format)
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
