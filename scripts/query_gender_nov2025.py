#!/usr/bin/env python3
"""Query candidatures by gender for November 2025."""

import sys
sys.path.insert(0, ".")

from skills.metabase_query.scripts.metabase import MetabaseAPI

api = MetabaseAPI()

# Requête SQL pour novembre 2025 - candidatures par genre
query = """
SELECT
    genre_candidat,
    COUNT(*) as nb_candidatures,
    COUNT(DISTINCT id_candidat) as nb_candidats_uniques
FROM public.candidatures_echelle_locale
WHERE date_candidature >= '2025-11-01'
  AND date_candidature < '2025-12-01'
  AND categorie_structure = 'IAE'
  AND type_structure IN ('AI', 'ACI', 'EI', 'EITI', 'ETTI')
GROUP BY genre_candidat
ORDER BY nb_candidatures DESC
"""

result = api.execute_sql(query)

print("=== Candidatures IAE novembre 2025 par genre ===")
print(f"{'Genre':<15} {'Candidatures':>15} {'Candidats uniques':>20}")
print("-" * 50)

total_cand = 0
total_uniq = 0
for row in result.rows:
    genre = row[0] if row[0] else "Non renseigné"
    nb_cand = row[1]
    nb_uniq = row[2]
    total_cand += nb_cand
    total_uniq += nb_uniq
    print(f"{genre:<15} {nb_cand:>15,} {nb_uniq:>20,}")

print("-" * 50)
print(f"{'TOTAL':<15} {total_cand:>15,} {total_uniq:>20,}")
