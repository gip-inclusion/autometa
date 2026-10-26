"""Rafraîchit data.json avec des valeurs de démonstration, sans appel réseau."""

import datetime
import json


def main() -> None:
    today = datetime.date.today()
    series = []
    for i in range(12):
        year, month = divmod(today.year * 12 + today.month - 12 + i, 12)
        series.append({"mois": f"{year}-{month + 1:02d}", "valeur": 800 + (i * 137 + today.day * 11) % 600})
    data = {"metadata": {"generated_at": today.isoformat(), "source": "Données de démonstration"}, "series": series}
    with open("data.json", "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    main()
