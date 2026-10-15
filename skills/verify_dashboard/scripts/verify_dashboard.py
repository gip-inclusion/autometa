"""Verify dashboard skill — thin wrapper over lib.viz_quality.verify_dashboard."""

import argparse
import json
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

from lib.viz_quality import verify_dashboard


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a dashboard headless and check its visual quality.")
    parser.add_argument("target", help="Dashboard slug, dashboard folder, or http(s) URL")
    parser.add_argument("--expect-charts", type=int, default=0, help="Minimum number of rendered charts")
    parser.add_argument("--screenshot", type=Path, help="Screenshot path (default: /tmp/verify_dashboard/<name>.png)")
    args = parser.parse_args()

    name = args.target.rstrip("/").rsplit("/", 1)[-1] or "page"
    screenshot = args.screenshot or Path(tempfile.gettempdir()) / "verify_dashboard" / f"{name}.png"
    try:
        result = verify_dashboard(args.target, screenshot, args.expect_charts)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
    except PlaywrightError as exc:
        print(
            f"Error: audit impossible ({exc}). Navigateur absent ? `uv run playwright install chromium`",
            file=sys.stderr,
        )
        sys.exit(2)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
