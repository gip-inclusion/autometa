"""CLI: create a one-shot pipeline from a composed system prompt and trigger a run, or relaunch one."""

import argparse
import json
import sys
from pathlib import Path

import httpx

from lib import jobs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Launch an autometa-jobs run from a composed system prompt.")
    parser.add_argument("--name", help="globally-unique pipeline name (e.g. dora-services-2026-06)")
    parser.add_argument("--system-prompt-file", help="path to the composed, self-contained prompt")
    parser.add_argument("--relaunch", metavar="PIPELINE_ID", help="trigger a new run of an existing pipeline instead")
    parser.add_argument("--max-turns", type=int, help="max agent turns (job autonomy budget)")
    parser.add_argument("--allowed-tools", help="comma-separated tools (e.g. Bash,Read,WebFetch)")
    parser.add_argument(
        "--output-format",
        choices=["md", "csv", "json", "txt"],
        help="artifact format: names the file (output.csv) and sets its content-type (default md)",
    )
    parser.add_argument("--input-uri", help="optional s3:// input for reusable pipelines")
    args = parser.parse_args(argv)
    if args.relaunch and (args.name or args.system_prompt_file):
        parser.error("--relaunch excludes --name and --system-prompt-file")
    if not (args.relaunch or (args.name and args.system_prompt_file)):
        parser.error("--relaunch PIPELINE_ID, or both --name and --system-prompt-file")

    overrides: dict = {}
    if args.max_turns:
        overrides["max_turns"] = args.max_turns
    if args.allowed_tools:
        overrides["allowed_tools"] = args.allowed_tools.split(",")
    if args.output_format:
        overrides["output_format"] = args.output_format
    try:
        if args.relaunch:
            out = jobs.launch(args.relaunch, input_uri=args.input_uri)
        else:
            system_prompt = Path(args.system_prompt_file).read_text()
            out = jobs.create_and_run(args.name, system_prompt, overrides or None, input_uri=args.input_uri)
    except httpx.HTTPError as exc:
        print(f"orchestrator error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
