"""CLI lecture seule pour Brevo : modèles, campagnes, volumes d'envoi par modèle. Jamais de contacts."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from lib import brevo  # noqa: E402
from lib.sources import list_instances  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Lire un compte Brevo (lecture seule, sans contacts).")
    ap.add_argument("--instance", help="compte Brevo (voir --instances), défaut : celui de config/sources.yaml")
    ap.add_argument("--instances", action="store_true", help="comptes Brevo configurés")
    ap.add_argument("--templates", action="store_true", help="modèles d'email du compte")
    ap.add_argument("--campaigns", action="store_true", help="campagnes du compte, avec leurs statistiques")
    ap.add_argument("--status", help="avec --campaigns : draft, scheduled, sent, suspended, archive...")
    ap.add_argument("--content", action="store_true", help="avec --templates ou --campaigns : inclure le HTML")
    ap.add_argument("--sends", action="store_true", help="nombre d'envois par modèle sur --days jours")
    ap.add_argument("--days", type=int, default=30, help=f"avec --sends : fenêtre en jours, {brevo.MAX_DAYS} au plus")
    args = ap.parse_args()

    if args.instances:
        out = list_instances("brevo")
    elif args.templates:
        out = brevo.run(args.instance, "templates", {"with_content": args.content})
    elif args.campaigns:
        given = {"status": args.status, "with_content": args.content}
        out = brevo.run(args.instance, "campaigns", {k: v for k, v in given.items() if v})
    elif args.sends:
        out = brevo.run(args.instance, "sends_by_template", {"days": args.days})
    else:
        ap.error("choisir --instances, --templates, --campaigns ou --sends")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
