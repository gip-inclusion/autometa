"""Régénère un rpe_templates.json candidat et imprime le rapport (ne remplace pas le fichier)."""

import json
import logging
from pathlib import Path

from lib.rpe_build import build_templates

logging.basicConfig(level=logging.INFO)


def main() -> None:
    candidate, report = build_templates()
    out = Path("rpe_templates.candidate.json")
    out.write_text(json.dumps(candidate, ensure_ascii=False, indent=0), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("candidate written to", out)


if __name__ == "__main__":
    main()
