#!/usr/bin/env python3
"""
Breakdown of prescriber visits on Les Emplois by organization type.
December 2025.
"""

from skills.matomo_query.scripts.matomo import MatomoAPI, format_data_source

api = MatomoAPI()

# Get organization type breakdown for prescribers
print("=" * 60)
print("Prescribers by Organization Type - Les Emplois - Dec 2025")
print("=" * 60)

# Query dimension 3 (UserOrganizationKind) filtered to prescribers
result = api.get_dimension(
    site_id=117,
    dimension_id=3,  # UserOrganizationKind
    period='month',
    date='2025-12-01',
    segment='dimension1==prescriber'  # filter to prescribers only
)

# Sort by visits descending
sorted_result = sorted(result, key=lambda x: x.get('nb_visits', 0), reverse=True)

# Calculate total visits
total_visits = sum(item.get('nb_visits', 0) for item in sorted_result)

print(f"\nTotal prescriber visits: {total_visits:,}")
print()

# Print table
print(f"{'Organization Type':<40} {'Visits':>10} {'%':>8} {'Actions':>12}")
print("-" * 72)

for item in sorted_result:
    label = item.get('label', 'Unknown')
    visits = item.get('nb_visits', 0)
    actions = item.get('nb_actions', 0)
    pct = (visits / total_visits * 100) if total_visits > 0 else 0

    if visits > 0:  # Only show non-zero entries
        print(f"{label:<40} {visits:>10,} {pct:>7.1f}% {actions:>12,}")

print("-" * 72)
print(f"{'TOTAL':<40} {total_visits:>10,} {'100.0%':>8}")

# Data source
print("\n" + "=" * 60)
print("Data Source:")
source = format_data_source(
    method='CustomDimensions.getCustomDimension',
    site_id=117,
    period='month',
    date='2025-12-01',
    extra_params={'idDimension': 3, 'segment': 'dimension1==prescriber'}
)
print(source)
