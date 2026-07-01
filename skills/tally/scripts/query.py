"""CLI lecture seule pour les formulaires et réponses Tally."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib.tally import TallyClient, list_workspaces  # noqa: E402


def forms_summary(client: TallyClient, workspace: str | None) -> list[dict]:
    items = client.list_forms(limit=500).get("items", [])
    if workspace:
        items = [f for f in items if f.get("workspaceId") == workspace]
    return [
        {
            "id": f.get("id"),
            "name": f.get("name"),
            "workspaceId": f.get("workspaceId"),
            "status": f.get("status"),
            "numberOfSubmissions": f.get("numberOfSubmissions"),
        }
        for f in items
    ]


def submissions(client: TallyClient, form_id: str, args) -> dict:
    rows = list(
        client.iter_submissions(
            form_id,
            filter=args.filter,
            start_date=args.since,
            end_date=args.until,
            limit=args.limit,
            max_pages=args.max_pages,
        )
    )
    return {
        "form_id": form_id,
        "count": len(rows),
        "questions": client.list_questions(form_id).get("questions", []),
        "submissions": rows,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Lire formulaires et réponses Tally (lecture seule).")
    ap.add_argument("--workspaces", action="store_true", help="workspaces visibles par la clé")
    ap.add_argument("--list", action="store_true", help="lister les formulaires")
    ap.add_argument("--workspace", metavar="WS_ID", help="filtrer --list sur un workspace (côté client)")
    ap.add_argument("--schema", metavar="FORM_ID", help="schéma courant d'un formulaire")
    ap.add_argument("--submissions", metavar="FORM_ID", help="réponses d'un formulaire")
    ap.add_argument("--filter", choices=["all", "completed", "partial"], help="statut des réponses")
    ap.add_argument("--since", metavar="ISO_DATE", help="réponses à partir de cette date (ISO 8601)")
    ap.add_argument("--until", metavar="ISO_DATE", help="réponses jusqu'à cette date (ISO 8601)")
    ap.add_argument("--limit", type=int, default=500, help="réponses par page (max 500)")
    ap.add_argument("--max-pages", type=int, default=20, help="plafond de pages de réponses")
    args = ap.parse_args()

    client = TallyClient()
    try:
        if args.workspaces:
            out: object = list_workspaces(client)
        elif args.list:
            out = forms_summary(client, args.workspace)
        elif args.schema:
            out = client.list_questions(args.schema).get("questions", [])
        elif args.submissions:
            out = submissions(client, args.submissions, args)
        else:
            ap.print_help()
            return
        print(json.dumps(out, ensure_ascii=False, indent=1))
    finally:
        client.close()


if __name__ == "__main__":
    main()
