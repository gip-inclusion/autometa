"""CLI de l'audit des conversations : une sous-commande par étape du run, sorties JSON ou markdown."""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[5]))

from web import audit, config  # noqa: E402


def dump(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=1, default=str))


def run_criteria(args) -> None:
    if args.propose:
        dump([c.model_dump() for c in audit.propose_criteria(Path(args.propose).read_text())])
    elif args.activate or args.retire:
        dump(
            audit.set_criterion_status(
                args.activate or args.retire, "actif" if args.activate else "retiré"
            ).model_dump()
        )
    else:
        dump([c.model_dump() for c in audit.load_criteria() if args.all or c.status == "actif"])


def run_slack(args) -> None:
    if args.post:
        print(f"{audit.post_slack(args.run, args.post, args.base_url)} message(s) publiés dans {args.post}.")
        return
    for message in audit.slack_messages(args.run, args.base_url):
        print(message["text"])
        for reply in message.get("thread", []):
            print(f"    ↳ {reply}")
        print()


COMMANDS = {
    "start": lambda a: dump(audit.start(a.kind, a.since, a.until).model_dump()),
    "extract": lambda a: dump(audit.extract(a.run, a.batches)),
    "show": lambda a: dump(audit.show(a.run, a.ids)),
    "criteria": run_criteria,
    "record": lambda a: dump(audit.record(a.run, Path(a.file).read_text())),
    "verify-list": lambda a: dump(audit.verify_list(a.run)),
    "merge": lambda a: dump(audit.merge(a.run)),
    "report": lambda a: print(audit.report(a.run, a.base_url)),
    "notion": lambda a: print(audit.export_notion(a.run, a.parent, a.base_url)),
    "findings": lambda a: dump(audit.findings_for(a.run)),
    "issues": lambda a: dump([
        i.model_dump() for i in (audit.upsert_issues(Path(a.upsert).read_text()) if a.upsert else audit.load_issues())
    ]),
    "lessons": lambda a: dump([
        lesson.model_dump()
        for lesson in (audit.upsert_lessons(Path(a.upsert).read_text()) if a.upsert else audit.load_lessons())
    ]),
    "slack": run_slack,
    "ticket": lambda a: print(audit.ticket(a.issue, a.base_url)),
    "finish": lambda a: dump(audit.finish(a.run, a.summary, a.abandon).model_dump()),
}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("start", help="ouvre un run")
    s.add_argument("--kind", choices=["daily", "weekly"], required=True)
    s.add_argument("--since", type=dt.date.fromisoformat, help="premier jour audité, au premier run seulement")
    s.add_argument("--until", type=dt.date.fromisoformat, help="jour exclu ; par défaut maintenant moins dix minutes")
    s = sub.add_parser("extract", help="transcriptions masquées, détections et lots")
    s.add_argument("--run", type=int, required=True)
    s.add_argument("--batches", type=int)
    s = sub.add_parser("show", help="messages complets, masqués")
    s.add_argument("--run", type=int, required=True)
    s.add_argument("ids", type=int, nargs="+")
    s = sub.add_parser("criteria", help="grille active ; --all, --propose, --activate, --retire")
    s.add_argument("--all", action="store_true")
    s.add_argument("--propose", metavar="FICHIER")
    s.add_argument("--activate", metavar="CODE")
    s.add_argument("--retire", metavar="CODE")
    s = sub.add_parser("record", help="enregistre la sortie d'audit d'un run quotidien")
    s.add_argument("--run", type=int, required=True)
    s.add_argument("file")
    s = sub.add_parser("verify-list", help="incidents graves à contre-vérifier, par lot (verify_NN.json)")
    s.add_argument("--run", type=int, required=True)
    s = sub.add_parser("merge", help="applique les contre-vérifications (verdict_NN.json) et enregistre")
    s.add_argument("--run", type=int, required=True)
    s = sub.add_parser("report", help="écrit le rapport markdown du run et affiche son chemin")
    s.add_argument("--run", type=int, required=True)
    s.add_argument("--base-url", default=config.PROD_URL)
    s = sub.add_parser("notion", help="publie le rapport du run sous une page Notion")
    s.add_argument("--run", type=int, required=True)
    s.add_argument("--parent", required=True, metavar="URL_DE_PAGE")
    s.add_argument("--base-url", default=config.PROD_URL)
    s = sub.add_parser("findings", help="incidents et observations hors grille d'un run")
    s.add_argument("--run", type=int, required=True)
    s = sub.add_parser("issues", help="problèmes systémiques ; --upsert pour créer ou relier")
    s.add_argument("--upsert", metavar="FICHIER")
    s = sub.add_parser("lessons", help="leçons proposées aux docs et prompts ; --upsert pour créer ou réécrire")
    s.add_argument("--upsert", metavar="FICHIER")
    s = sub.add_parser("slack", help="affiche les messages du run ; --post CANAL les publie")
    s.add_argument("--run", type=int, required=True)
    s.add_argument("--post", metavar="CANAL")
    s.add_argument("--base-url", default=config.PROD_URL)
    s = sub.add_parser("ticket", help="ticket Notion d'un problème systémique, en markdown")
    s.add_argument("--issue", required=True)
    s.add_argument("--base-url", default=config.PROD_URL)
    s = sub.add_parser("finish", help="clôt le run, ou l'abandonne")
    s.add_argument("--run", type=int, required=True)
    s.add_argument("--summary", default="")
    s.add_argument("--abandon", action="store_true")
    return p


def main() -> None:
    args = parser().parse_args()
    try:
        COMMANDS[args.command](args)
    except audit.AuditError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
