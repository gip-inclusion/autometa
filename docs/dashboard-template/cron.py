"""Rafraîchit data.json. Tourne périodiquement via /cron."""

import datetime
import json

from lib.dashboard_api import query_matomo

# `lib.dashboard_api` est le seul module du dépôt qu'un dashboard a le droit d'importer : c'est le
# contrat sur lequel l'application s'engage. Tout le reste (lib.query, web.db, web.config) est
# interne et peut changer sans préavis — l'import est refusé à l'enregistrement et signalé au cron.

# Ce cron ne lit et n'écrit que dans le dossier de son propre dashboard. En production
# il tourne isolé dans un répertoire temporaire — les autres dashboards n'existent pas
# à côté de lui. Ne jamais lire ../autre-dashboard/ ni /app/data/interactive/autre/ :
# ces chemins ne résolvent rien. Si des données d'un autre dashboard sont nécessaires,
# les régénérer ici depuis la source primaire (Matomo, Metabase, GitHub…).


def main() -> None:
    # TODO : remplacer par la requête du dashboard — query_matomo, query_metabase,
    # query_autometa_tables, query_data_inclusion ou query_storage.
    result = query_matomo("inclusion", "VisitsSummary.get", {"idSite": 117, "period": "month", "date": "today"})
    if not result.success:
        raise SystemExit(f"Requête en échec : {result.error}")

    data = {
        "metadata": {
            "generated_at": datetime.date.today().isoformat(),
            "source": "Matomo API - VisitsSummary.get",
        },
        "visites": result.data,
    }
    with open("data.json", "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    main()
