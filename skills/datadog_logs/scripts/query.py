"""CLI lecture seule pour les logs Datadog : compter, échantillonner, agréger, dumper."""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib.datadog import DatadogClient, by_count, day_windows, window  # noqa: E402

DEFAULT_FIELDS = [
    "http.url",
    "http.url_details.view_name",
    "http.status_code",
    "usr.id",
    "usr.kind",
    "usr.organization_type",
]


def pluck(event: dict, fields: list[str]) -> dict:
    attributes = event["attributes"]["attributes"]
    row = {"ts": event["attributes"]["timestamp"]}
    for field in fields:
        value = attributes
        for part in field.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        row[field] = value
    return row


def dump(client: DatadogClient, args) -> dict:
    fields = args.field or DEFAULT_FIELDS
    windows = day_windows(args.days, args.chunk)
    out = Path(args.dump)
    out.parent.mkdir(parents=True, exist_ok=True)

    def fetch(window: tuple[str, str]) -> list[dict]:
        frm, to = window
        return [pluck(event, fields) for event in client.iter_events(args.query, frm, to)]

    # Why: écrire chaque tranche dès qu'elle arrive borne la mémoire et laisse un fichier exploitable
    # si une tranche échoue après un quart d'heure de quota consommé.
    total = 0
    with out.open("w") as handle, ThreadPoolExecutor(max_workers=args.workers) as pool:
        for batch in pool.map(fetch, windows):
            for row in batch:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                total += 1
    return {"file": str(out), "events": total, "windows": len(windows), "fields": fields}


def aggregate(client: DatadogClient, args) -> list[dict]:
    frm, to = window(args.days)
    compute = [{"aggregation": "count"}]
    if args.distinct:
        compute.append({"aggregation": "cardinality", "metric": args.distinct})
    group_by = [by_count(facet, args.top) for facet in args.group_by]
    buckets = client.aggregate(args.query, frm, to, group_by=group_by, compute=compute)
    rows = [
        {"by": bucket["by"], "count": bucket["computes"].get("c0", 0)}
        | ({"distinct": bucket["computes"].get("c1", 0)} if args.distinct else {})
        for bucket in buckets
    ]
    return sorted(rows, key=lambda row: -row["count"])


def main() -> None:
    ap = argparse.ArgumentParser(description="Lire les logs Datadog (lecture seule).")
    ap.add_argument("--query", required=True, help="filtre Datadog, ex. 'service:itou-prod @http.method:GET'")
    ap.add_argument("--days", type=int, default=7, help="profondeur en jours (rétention : 30 max)")
    ap.add_argument("--distinct", metavar="FACETTE", help="cardinalité d'une facette (par défaut : comptage)")
    ap.add_argument("--search", action="store_true", help="échantillon d'événements bruts")
    ap.add_argument("--limit", type=int, default=10, help="taille de l'échantillon --search")
    ap.add_argument("--group-by", action="append", default=[], metavar="FACETTE", help="agréger par facette")
    ap.add_argument("--top", type=int, default=50, help="nombre de valeurs par facette")
    ap.add_argument("--dump", metavar="FICHIER", help="tout écrire en JSONL")
    ap.add_argument("--chunk", type=int, default=1, help="taille des tranches du dump, en jours")
    ap.add_argument("--field", action="append", default=[], help="champ à conserver au dump (répétable)")
    ap.add_argument("--workers", type=int, default=4, help="parallélisme du dump (le quota reste global)")
    args = ap.parse_args()

    with DatadogClient() as client:
        if args.dump:
            result = dump(client, args)
        elif args.group_by:
            result = aggregate(client, args)
        elif args.search:
            frm, to = window(args.days)
            result = [
                pluck(event, args.field or DEFAULT_FIELDS)
                for event in client.iter_events(args.query, frm, to, max_events=args.limit)
            ]
        else:
            result = client.count(args.query, *window(args.days), distinct=args.distinct)

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
