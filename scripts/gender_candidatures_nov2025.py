#!/usr/bin/env python3
"""Gender distribution in IAE candidatures for November 2025."""

from skills.metabase_query.scripts.metabase import MetabaseAPI

api = MetabaseAPI()

query = """
SELECT
    genre_candidat,
    COUNT(*) AS nb_candidatures
FROM public.candidatures_echelle_locale
WHERE categorie_structure = 'IAE'
  AND type_structure IN ('AI', 'ACI', 'EI', 'EITI', 'ETTI')
  AND date_candidature >= '2025-11-01'
  AND date_candidature < '2025-12-01'
GROUP BY genre_candidat
ORDER BY nb_candidatures DESC
"""

result = api.execute_sql(query)
print(result.to_markdown())

# Calculate percentages
total = sum(row[1] for row in result.rows)
print(f"\n**Total candidatures IAE novembre 2025 : {total:,}**\n")
print("| Genre | Nombre | Pourcentage |")
print("|-------|--------|-------------|")
for row in result.rows:
    genre, count = row[0], row[1]
    pct = (count / total * 100) if total > 0 else 0
    print(f"| {genre or 'Non renseigné'} | {count:,} | {pct:.1f}% |")
