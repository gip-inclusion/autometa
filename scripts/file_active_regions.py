#!/usr/bin/env python3
"""
Query file active candidates by region.
Uses Metabase card 7294 which shows "Répartition candidats dans la file active par région"
"""

import sys
sys.path.insert(0, '.')

from skills.metabase_query.scripts.metabase import MetabaseAPI, format_data_source

api = MetabaseAPI()

print("=== Candidats dans la file active IAE par région ===")
print("(Candidats en recherche active, première candidature >30 jours, aucune acceptée)")
print()

# Execute the card
result = api.execute_card(7294, timeout=120)

# Print results
print(result.to_markdown())

# Calculate total
total = sum(row[1] for row in result.rows if row[1])
print(f"\nTotal France : {total:,} candidats".replace(",", " "))

# Data source
print()
print("**Data source:**", format_data_source(
    api.url,
    card_id=7294,
    sql="SELECT région, COUNT(DISTINCT id) FROM candidats_recherche_active WHERE delai_premiere_candidature > 30 AND nb_candidatures_acceptees = 0 GROUP BY région"
))
