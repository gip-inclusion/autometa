"""CLI lecture seule pour Brevo : modèles, campagnes, volumes d'envoi par modèle, totaux. Jamais de contacts."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import brevo  # noqa: E402
from lib.sources import list_instances  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Lire un compte Brevo (lecture seule, sans contacts).")
    ap.add_argument("--instance", default="marketing", help="compte Brevo (voir --instances), défaut marketing")
    ap.add_argument("--instances", action="store_true", help="comptes Brevo configurés")
    ap.add_argument("--templates", action="store_true", help="modèles d'email du compte")
    ap.add_argument("--campaigns", action="store_true", help="campagnes du compte, avec leurs statistiques")
    ap.add_argument("--status", help="avec --campaigns : draft, scheduled, sent, suspended, archive...")
    ap.add_argument("--content", action="store_true", help="avec --templates ou --campaigns : inclure le HTML")
    ap.add_argument("--sends", action="store_true", help="nombre d'envois par modèle sur --days jours")
    ap.add_argument("--event", default="requests", help=f"avec --sends : {', '.join(brevo.EVENTS)}")
    ap.add_argument("--report", action="store_true", help="totaux des emails transactionnels sur --days jours")
    ap.add_argument("--tag", help="avec --report : limiter à un tag")
    ap.add_argument("--days", type=int, default=30, help=f"fenêtre en jours, {brevo.MAX_DAYS} au plus")
    args = ap.parse_args()

    if args.instances:
        out = list_instances("brevo")
    elif args.templates:
        out = brevo.run(args.instance, "templates", {"with_content": args.content})
    elif args.campaigns:
        out = brevo.run(args.instance, "campaigns", {"status": args.status, "with_content": args.content})
    elif args.sends:
        out = brevo.run(args.instance, "sends_by_template", {"days": args.days, "event": args.event})
    elif args.report:
        out = brevo.run(args.instance, "report", {"days": args.days, "tag": args.tag})
    else:
        ap.error("choisir --instances, --templates, --campaigns, --sends ou --report")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
