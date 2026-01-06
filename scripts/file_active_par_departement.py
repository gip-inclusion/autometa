#!/usr/bin/env python3
"""
Candidats dans la file active par département.
Définition : candidats avec première candidature il y a + de 30 jours,
et aucune candidature acceptée à ce jour.
"""

import sys
sys.path.insert(0, '/Users/louije/Development/gip/Matometa')

from skills.metabase_query.scripts.metabase import MetabaseAPI

query = """
SELECT
    département,
    nom_département,
    région,
    COUNT(DISTINCT id) as nb_candidats
FROM public.candidats_recherche_active
WHERE delai_premiere_candidature > 30
  AND nb_candidatures_acceptees = 0
  AND département IS NOT NULL
GROUP BY département, nom_département, région
ORDER BY nb_candidats DESC
"""

api = MetabaseAPI()
result = api.execute_sql(query)
print(result.to_markdown())
