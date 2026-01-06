#!/usr/bin/env python3
"""Query employer visits by organization type for December 2025."""

import sys
sys.path.insert(0, '/Users/louije/Development/gip/Matometa')

from skills.matomo_query.scripts.matomo import MatomoAPI

api = MatomoAPI()
data = api.get_dimension(
    site_id=117,
    dimension_id=3,
    period='month',
    date='2025-12-01',
    segment='dimension1==employer',
    limit=100
)

# Sort by nb_visits descending
sorted_data = sorted(data, key=lambda x: x.get('nb_visits', 0), reverse=True)

print('| Type d\'organisation | Visites | % | Actions | Moy. actions/visite |')
print('|---------------------|---------|---|---------|---------------------|')
total_visits = sum(d.get('nb_visits', 0) for d in sorted_data)
for item in sorted_data:
    label = item.get('label', 'Unknown')
    if label == '-':
        label = '(non renseigné)'
    visits = item.get('nb_visits', 0)
    actions = item.get('nb_actions', 0)
    avg = actions / visits if visits > 0 else 0
    pct = (visits / total_visits * 100) if total_visits > 0 else 0
    print(f'| {label:19} | {visits:>7,} | {pct:>5.1f}% | {actions:>7,} | {avg:>19.1f} |')

print(f'\n**Total employeurs:** {total_visits:,} visites')
