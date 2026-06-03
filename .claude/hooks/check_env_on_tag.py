#!/usr/bin/env python3
"""PostToolUse hook: remind to copy env vars before prod deploy after git tag."""

import json
import sys


def main():
    data = json.load(sys.stdin)
    command = data.get("tool_input", {}).get("command", "")

    if "git tag" not in command:
        sys.exit(0)

    print("Rappel : as-tu bien copié les variables d'environnement de staging vers la prod ?")


if __name__ == "__main__":
    main()
