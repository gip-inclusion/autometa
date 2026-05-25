"""Rafraîchit data.json. Tourne périodiquement via /cron."""

import datetime
import json

# Ce cron ne lit et n'écrit que dans le dossier de son propre dashboard. En production
# il tourne isolé dans un répertoire temporaire — les autres dashboards n'existent pas
# à côté de lui. Ne jamais lire ../autre-dashboard/ ni /app/data/interactive/autre/ :
# ces chemins ne résolvent rien. Si des données d'un autre dashboard sont nécessaires,
# les régénérer ici depuis la source primaire (Matomo, Metabase, GitHub…).


def main() -> None:
    # TODO : appeler lib.query.execute_matomo_query ou execute_metabase_query
    # et remplir `data` avec le résultat. Voir docs/interactive-dashboards.md.
    data = {
        "metadata": {
            "generated_at": datetime.date.today().isoformat(),
            "source": "TODO",
        },
    }
    with open("data.json", "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    main()
