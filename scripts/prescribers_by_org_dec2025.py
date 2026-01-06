#!/usr/bin/env python3
"""
Breakdown of prescribers visiting les Emplois in December 2025, by organisation type.
Uses Custom Dimension 3 (UserOrganizationKind) with segment on Dimension 1 (UserKind=prescriber).
"""

from skills.matomo_query.scripts.matomo import MatomoAPI

SITE_ID = 117  # Les Emplois
PERIOD = 'month'
DATE = '2025-12-01'
SEGMENT = 'dimension1==prescriber'

def main():
    api = MatomoAPI()

    # Get total prescriber visits for context
    print("=== Total Prescriber Traffic (Dec 2025) ===\n")
    visits = api.get_visits(
        site_id=SITE_ID,
        period=PERIOD,
        date=DATE,
        segment=SEGMENT
    )
    print(f"Visits: {visits.get('nb_visits', 'N/A'):,}")
    print(f"Unique visitors: {visits.get('nb_uniq_visitors', 'N/A'):,}")
    print(f"Actions: {visits.get('nb_actions', 'N/A'):,}")
    print(f"Actions per visit: {visits.get('nb_actions_per_visit', 'N/A')}")

    # Get breakdown by organization type
    print("\n=== Breakdown by Organisation Type ===\n")
    org_data = api.get_dimension(
        site_id=SITE_ID,
        dimension_id=3,  # UserOrganizationKind
        period=PERIOD,
        date=DATE,
        segment=SEGMENT
    )

    if not org_data:
        print("No data returned.")
        return

    # Sort by visits descending
    sorted_orgs = sorted(org_data, key=lambda x: x.get('nb_visits', 0), reverse=True)

    # Calculate total for percentages
    total_visits = sum(item.get('nb_visits', 0) for item in sorted_orgs)

    # Print markdown table
    print("| Type d'organisation | Visites | % du total | Actions | Actions/visite |")
    print("|---------------------|---------|------------|---------|----------------|")

    for item in sorted_orgs:
        label = item.get('label', 'Unknown')
        nb_visits = item.get('nb_visits', 0)
        nb_actions = item.get('nb_actions', 0)
        actions_per_visit = item.get('nb_actions_per_visit', 0)
        pct = (nb_visits / total_visits * 100) if total_visits > 0 else 0

        print(f"| {label} | {nb_visits:,} | {pct:.1f}% | {nb_actions:,} | {actions_per_visit:.1f} |")

    print(f"\n**Total:** {total_visits:,} visites")

if __name__ == '__main__':
    main()
