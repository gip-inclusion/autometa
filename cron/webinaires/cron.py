#!/usr/bin/env python3
"""Cron wrapper: daily Grist webinaires sync."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "sync_webinaires.py"

sys.exit(subprocess.call([sys.executable, str(SCRIPT), "--grist-only"]))
