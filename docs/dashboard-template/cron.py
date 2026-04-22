"""Rafraîchit data.json. Tourne quotidiennement via /cron."""

import datetime
import json


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
