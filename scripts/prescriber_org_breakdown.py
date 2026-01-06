#!/usr/bin/env python3
"""
Breakdown of prescriber visits by organization type - December 2025
Site: Les Emplois (ID 117)
"""

from skills.matomo_query.scripts.matomo import MatomoAPI, format_data_source

api = MatomoAPI()

# Get organization type breakdown for prescribers
result = api.get_dimension(
    site_id=117,
    dimension_id=3,  # UserOrganizationKind
    period='month',
    date='2025-12-01',
    segment='dimension1==prescriber'  # filter to prescribers only
)

# Sort by visits descending
sorted_result = sorted(result, key=lambda x: x.get('nb_visits', 0), reverse=True)

# Calculate total
total_visits = sum(item.get('nb_visits', 0) for item in sorted_result)

print("## Répartition des prescripteurs par type d'organisation - Décembre 2025\n")
print(f"**Total visites prescripteurs :** {total_visits:,}\n")
print("| Type d'organisation | Visites | % du total |")
print("|---------------------|---------|------------|")

for item in sorted_result:
    label = item.get('label', 'Unknown')
    visits = item.get('nb_visits', 0)
    pct = (visits / total_visits * 100) if total_visits > 0 else 0
    print(f"| {label} | {visits:,} | {pct:.1f}% |")

print("\n" + format_data_source(
    method="CustomDimensions.getCustomDimension",
    site_id=117,
    period="month",
    date="2025-12-01",
    segment="dimension1==prescriber",
    extra_params={"idDimension": 3}
))
