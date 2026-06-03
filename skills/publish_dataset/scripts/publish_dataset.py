"""CLI: run SQL against a PG source and publish the result(s) as a job-accessible dataset."""

import argparse
import json
import sys

from lib import job_inputs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Publish SQL query result(s) as a job dataset (sqlite/jsonl/csv).")
    parser.add_argument("--slug", required=True, help="dataset name ([a-z0-9_-]); becomes the S3 filename")
    parser.add_argument("--source", required=True, choices=["autometa_tables_db", "data_inclusion"])
    parser.add_argument("--sql", help="single query -> one table (use --format for jsonl/csv)")
    parser.add_argument(
        "--tables",
        help='JSON object {table_name: sql} -> one sqlite file with several JOIN-able tables',
    )
    parser.add_argument("--format", default="sqlite", choices=["sqlite", "jsonl", "csv"])
    args = parser.parse_args(argv)

    try:
        if args.tables:
            queries = json.loads(args.tables)
            out = job_inputs.publish_query_tables(args.slug, args.source, queries)
        elif args.sql:
            out = job_inputs.publish_query(args.slug, args.source, args.sql, fmt=args.format)
        else:
            parser.error("provide --sql (single table) or --tables (multi-table sqlite)")
    except json.JSONDecodeError as exc:
        print(f"--tables is not valid JSON: {exc}", file=sys.stderr)
        return 1
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
