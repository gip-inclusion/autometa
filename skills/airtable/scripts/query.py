"""CLI lecture seule pour les tables et enregistrements Airtable."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib.airtable import MAX_PAGES, AirtableClient, AirtableError  # noqa: E402


def tables_summary(client: AirtableClient, base_id: str) -> list[dict]:
    return [
        {
            "id": t.get("id"),
            "name": t.get("name"),
            "fields": [{"id": f.get("id"), "name": f.get("name"), "type": f.get("type")} for f in t.get("fields", [])],
            "views": [{"id": v.get("id"), "name": v.get("name")} for v in t.get("views", [])],
        }
        for t in client.list_tables(base_id)
    ]


def run(args) -> object:
    with AirtableClient() as client:
        if args.command == "tables":
            return tables_summary(client, args.base_id)
        records = client.list_records(
            args.base_id, args.table, view=args.view, fields=args.field, formula=args.formula, max_pages=args.max_pages
        )
        return {"count": len(records), "records": records}


def main() -> None:
    ap = argparse.ArgumentParser(description="Lire les tables et enregistrements Airtable (lecture seule).")
    sub = ap.add_subparsers(dest="command", required=True)
    tables = sub.add_parser("tables", help="tables d'une base, avec leurs champs et leurs vues")
    tables.add_argument("base_id", help="identifiant de base (app…)")
    records = sub.add_parser("records", help="enregistrements d'une table ou d'une vue")
    records.add_argument("base_id", help="identifiant de base (app…)")
    records.add_argument("table", help="identifiant (tbl…) ou nom de table")
    records.add_argument("--view", help="identifiant (viw…) ou nom de vue")
    records.add_argument("--field", action="append", help="champ à renvoyer (répétable)")
    records.add_argument("--formula", help="filtre filterByFormula, ex. \"{Statut} = 'À valider'\"")
    records.add_argument("--max-pages", type=int, default=MAX_PAGES, help="plafond de pages de 100 enregistrements")
    args = ap.parse_args()

    try:
        out = run(args)
    except AirtableError as e:
        sys.exit(f"Erreur Airtable : {e}")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
