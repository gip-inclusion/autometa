"""CLI pour explorer le catalogue RPE et lancer des requêtes à la demande."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib.rpe import RpeClient  # noqa: E402


def parse_dim(spec: str):
    if ":" in spec:
        dim, lpos = spec.split(":", 1)
        return {"dim": dim, "hPos": 0, "lPos": int(lpos)}
    return spec


def main() -> None:
    ap = argparse.ArgumentParser(description="Requêter le tableau de bord RPE (DigDash).")
    ap.add_argument("--list", action="store_true", help="lister les datasets")
    ap.add_argument("--measures", metavar="DATASET", help="lister les mesures d'un dataset")
    ap.add_argument("--dims", metavar="DATASET", help="lister les dimensions d'un dataset")
    ap.add_argument("--query", metavar="DATASET", help="dataset à requêter")
    ap.add_argument("--dim", action="append", default=[], help="dimension (id ou id:lPos), répétable")
    ap.add_argument("--measure", action="append", default=[], help="measure_id exact, répétable (défaut: toutes)")
    args = ap.parse_args()

    client = RpeClient.connect()
    try:
        if args.list:
            print(json.dumps(client.datasets(), ensure_ascii=False, indent=1))
        elif args.measures:
            print(json.dumps(client.measures(args.measures), ensure_ascii=False, indent=1))
        elif args.dims:
            print(json.dumps(client.dimensions(args.dims), ensure_ascii=False, indent=1))
        elif args.query:
            rows = client.query(
                args.query,
                dimensions=[parse_dim(d) for d in args.dim],
                measures=args.measure or None,
            )
            print(json.dumps(rows, ensure_ascii=False, indent=1))
        else:
            ap.print_help()
    finally:
        client.close()


if __name__ == "__main__":
    main()
