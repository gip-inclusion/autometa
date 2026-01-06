#!/usr/bin/env python3
"""
Analyse des prescripteurs sur les Emplois par type d'organisation
Décembre 2024
"""

from skills.matomo_query.scripts.matomo import MatomoAPI, format_data_source

SITE_ID = 117
PERIOD = 'month'
DATE = '2024-12-01'

def main():
    api = MatomoAPI()

    # 1. Get total visits from prescribers in December 2024
    print("=" * 60)
    print("PRESCRIPTEURS LES EMPLOIS - DÉCEMBRE 2024")
    print("=" * 60)

    prescriber_segment = 'dimension1==prescriber'

    # Get overall prescriber stats
    visits = api.get_visits(
        site_id=SITE_ID,
        period=PERIOD,
        date=DATE,
        segment=prescriber_segment
    )

    print(f"\n## Vue d'ensemble des prescripteurs")
    print(f"- Visites totales : {visits.get('nb_visits', 'N/A'):,}")
    print(f"- Visiteurs uniques : {visits.get('nb_uniq_visitors', 'N/A'):,}")
    print(f"- Actions : {visits.get('nb_actions', 'N/A'):,}")

    print(format_data_source(
        method='VisitsSummary.get',
        site_id=SITE_ID,
        period=PERIOD,
        date=DATE,
        segment=prescriber_segment
    ))

    # 2. Get breakdown by organization type (dimension 3)
    print(f"\n## Ventilation par type d'organisation")

    org_breakdown = api.get_dimension(
        site_id=SITE_ID,
        dimension_id=3,  # UserOrganizationKind
        period=PERIOD,
        date=DATE,
        segment=prescriber_segment
    )

    if not org_breakdown:
        print("Pas de données disponibles")
        return

    # Sort by visits descending
    sorted_orgs = sorted(org_breakdown, key=lambda x: x.get('nb_visits', 0), reverse=True)

    # Calculate total for percentages
    total_visits = sum(org.get('nb_visits', 0) for org in sorted_orgs)

    print(f"\n| Type d'organisation | Visites | % du total |")
    print(f"|---------------------|--------:|-----------:|")

    for org in sorted_orgs:
        label = org.get('label', 'Inconnu')
        nb_visits = org.get('nb_visits', 0)
        pct = (nb_visits / total_visits * 100) if total_visits > 0 else 0
        print(f"| {label} | {nb_visits:,} | {pct:.1f}% |")

    print(f"| **Total** | **{total_visits:,}** | **100%** |")

    print(format_data_source(
        method='CustomDimensions.getCustomDimension',
        site_id=SITE_ID,
        period=PERIOD,
        date=DATE,
        segment=prescriber_segment,
        extra_params={'idDimension': 3}
    ))

if __name__ == '__main__':
    main()
