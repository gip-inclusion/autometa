#!/usr/bin/env python3
"""
Récupère l'évolution des visiteurs et actions sur RDV-Insertion pour 2025.
"""

import sys
sys.path.insert(0, '.')

from skills.matomo_query.scripts.matomo import MatomoAPI

api = MatomoAPI()

# Récupérer les données mensuelles 2025
data = api.get_visits(
    site_id=214,
    period="month",
    date="2025-01-01,2025-12-31"
)

print("# Données mensuelles RDV-Insertion 2025")
print()
print("| Mois | Visiteurs uniques | Visites | Actions | Actions/visite |")
print("|------|-------------------|---------|---------|----------------|")

months = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]

for i, (date_key, stats) in enumerate(sorted(data.items())):
    if isinstance(stats, dict) and 'nb_uniq_visitors' in stats:
        visitors = stats.get('nb_uniq_visitors', 0)
        visits = stats.get('nb_visits', 0)
        actions = stats.get('nb_actions', 0)
        actions_per_visit = stats.get('nb_actions_per_visit', 0)
        month_name = months[i] if i < len(months) else date_key
        print(f"| {month_name} 2025 | {visitors:,} | {visits:,} | {actions:,} | {actions_per_visit:.1f} |")

# Données pour le graphique Mermaid
print()
print("## Données pour graphique Mermaid")
print()

visitors_list = []
actions_list = []
months_short = []

for i, (date_key, stats) in enumerate(sorted(data.items())):
    if isinstance(stats, dict) and 'nb_uniq_visitors' in stats:
        visitors_list.append(stats.get('nb_uniq_visitors', 0))
        # Actions en milliers pour échelle lisible
        actions_list.append(round(stats.get('nb_actions', 0) / 1000, 1))
        months_short.append(months[i] if i < len(months) else "?")

print(f"Mois: {months_short}")
print(f"Visiteurs: {visitors_list}")
print(f"Actions (k): {actions_list}")
