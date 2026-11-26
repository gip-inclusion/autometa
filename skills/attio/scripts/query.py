"""CLI lecture seule pour le CRM Attio : objets, attributs, enregistrements, listes."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib.attio import AttioError, run  # noqa: E402


def request(args: argparse.Namespace) -> tuple[str, dict] | None:
    query_filter = json.loads(args.filter) if args.filter else None
    fields = args.fields.split(",") if args.fields else None
    if args.objects:
        return "objects", {}
    if args.attributes and args.options:
        return "options", {"object": args.attributes, "attribute": args.options}
    if args.attributes:
        return "attributes", {"object": args.attributes}
    if args.search:
        return "records", {"object": args.search, "filter": query_filter, "fields": fields, "limit": args.limit}
    if args.count:
        return "count", {"object": args.count, "filter": query_filter, "by": args.by}
    if args.lists:
        return "lists", {}
    if args.entries:
        return "entries", {"list": args.entries, "filter": query_filter, "fields": fields}
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Lire le CRM Attio (lecture seule).")
    ap.add_argument("--objects", action="store_true", help="objets du CRM (people, companies, deals...)")
    ap.add_argument("--attributes", metavar="OBJET", help="attributs d'un objet")
    ap.add_argument("--options", metavar="ATTRIBUT", help="avec --attributes : valeurs possibles d'un attribut select")
    ap.add_argument("--search", metavar="OBJET", help="enregistrements d'un objet, filtrés par --filter")
    ap.add_argument("--count", metavar="OBJET", help="nombre d'enregistrements d'un objet, filtrés par --filter")
    ap.add_argument("--by", metavar="ATTRIBUT", help="avec --count : répartition par valeur d'un attribut")
    ap.add_argument("--lists", action="store_true", help="listes du CRM (pipes)")
    ap.add_argument("--entries", metavar="LISTE", help="entrées d'une liste (slug ou identifiant)")
    ap.add_argument("--filter", metavar="JSON", help='query_filter Attio, ex. \'{"type_de_compte": "CCAS"}\'')
    ap.add_argument("--fields", metavar="A,B", help="attributs à garder dans la sortie")
    ap.add_argument("--limit", type=int, default=50, help="nombre maximal d'enregistrements rendus par --search")
    args = ap.parse_args()
    try:
        asked = request(args)
        if asked is None:
            ap.print_help()
            return
        out = run(*asked)
    except (AttioError, json.JSONDecodeError) as e:
        sys.exit(f"Erreur Attio : {e}")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
