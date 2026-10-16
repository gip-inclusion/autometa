"""Verify dashboard skill — thin wrapper over lib.dashboard_quality.verify."""

import argparse
import json
import sys

from playwright.sync_api import Error as PlaywrightError

from lib.dashboard_quality import verify


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a dashboard headless and report its visual issues.")
    parser.add_argument("target", help="Dashboard slug (data/interactive/{slug}/) or folder path")
    parser.add_argument("--expect-charts", type=int, default=0, help="Minimum number of charts that must be drawn")
    args = parser.parse_args()

    try:
        result = verify(args.target, args.expect_charts)
    except PlaywrightError as error:
        print(f"audit impossible, aucun verdict : {error}", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
