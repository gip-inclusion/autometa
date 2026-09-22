"""Rafraîchit un fichier de données par déclinaison déclarée. Tourne périodiquement via /cron."""

import datetime
import json
from pathlib import Path

from lib.dashboard_api import list_variants, query_matomo

# `lib.dashboard_api` est le seul module du dépôt qu'un dashboard a le droit d'importer : c'est le
# contrat sur lequel l'application s'engage. Tout le reste (lib.query, web.db, web.config) est
# interne et peut changer sans préavis — l'import est refusé à l'enregistrement et signalé au cron.

# Un tableau de bord multi-sources sert plusieurs déclinaisons (un département, une structure, un
# site…) avec le même écran. Les déclinaisons sont déclarées par le skill update_dashboard ; ce cron
# ne produit que celles-là, une par fichier `data/<jeton>.json`, et rien d'autre : aucun fichier qui
# les énumère, sinon le lien de chacune n'est plus privé. Les mêmes calculs servent chaque
# déclinaison — seule la clé varie. La source est interrogée une fois pour toutes, puis découpée.


def fetch_by_key() -> dict[str, dict]:
    # TODO : remplacer par la requête du dashboard, en une seule passe pour toutes les clés —
    # query_matomo, query_metabase, query_autometa_tables, query_data_inclusion ou query_storage.
    result = query_matomo("inclusion", "VisitsSummary.get", {"idSite": "all", "period": "month", "date": "today"})
    if not result.success:
        raise SystemExit(f"Requête en échec : {result.error}")
    return {str(key): payload for key, payload in result.data.items()}


def assemble(variant: dict, payload: dict) -> dict:
    # Le fichier porte la clé et le libellé de sa déclinaison — jamais son jeton.
    return {
        "metadata": {
            "generated_at": datetime.date.today().isoformat(),
            "source": "Matomo API - VisitsSummary.get",
            "key": variant["key"],
            "label": variant["label"],
        },
        "visites": payload,
    }


def main() -> None:
    declared = list_variants()
    if not declared:
        print("Aucune déclinaison déclarée : rien à produire.")
        return

    by_key = fetch_by_key()
    failed = []
    for variant in declared:
        payload = by_key.get(variant["key"])
        if payload is None:
            failed.append(variant["key"])
            continue
        try:
            data = assemble(variant, payload)
        except Exception as exc:  # noqa: BLE001
            # Why: une déclinaison dont l'assemblage casse ne doit pas priver les autres de leur
            # rafraîchissement ; son fichier précédent reste en place et le run finira en échec.
            print(f"{variant['key']} ({variant['label']}) : échec — {exc}")
            failed.append(variant["key"])
            continue
        path = Path(variant["path"])
        path.parent.mkdir(exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"{variant['key']} ({variant['label']}) : écrit")

    if failed:
        # Code 3 : run partiel — l'outillage conserve les fichiers écrits et marque le run en échec.
        print(f"Déclinaisons sans données, fichier précédent conservé : {', '.join(failed)}")
        raise SystemExit(3)


if __name__ == "__main__":
    main()
