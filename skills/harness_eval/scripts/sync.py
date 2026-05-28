"""Push/pull the eval corpus between a local dir and S3."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import eval_corpus


def cmd_push(args: argparse.Namespace) -> None:
    local = Path(args.local_dir)
    if not local.exists():
        print(json.dumps({"error": f"Local dir {local} does not exist"}))
        sys.exit(1)
    count = eval_corpus.push_local_corpus(local, subpath=args.subpath)
    print(json.dumps({"pushed": count, "local_dir": str(local), "s3_subpath": args.subpath}))


def cmd_pull(args: argparse.Namespace) -> None:
    local = Path(args.local_dir)
    count = eval_corpus.pull_corpus_to_dir(local, subpath=args.subpath)
    print(json.dumps({"pulled": count, "local_dir": str(local), "s3_subpath": args.subpath}))


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync eval corpus between local and S3")
    sub = parser.add_subparsers(dest="command", required=True)

    push = sub.add_parser("push", help="Push local dir to s3://eval_corpus/<subpath>")
    push.add_argument("--local-dir", required=True)
    push.add_argument("--subpath", default="", help="Optional S3 sub-prefix (e.g. 'sessions/')")

    pull = sub.add_parser("pull", help="Pull s3://eval_corpus/<subpath> to local dir")
    pull.add_argument("--local-dir", required=True)
    pull.add_argument("--subpath", default="", help="Optional S3 sub-prefix")

    args = parser.parse_args()
    {"push": cmd_push, "pull": cmd_pull}[args.command](args)


if __name__ == "__main__":
    main()
