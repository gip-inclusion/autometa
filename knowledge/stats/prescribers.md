# Prescripteurs habilités

*Dernière mise à jour : 2025-01-03*

## Source

Table : `public.taux_transformation_prescripteurs`
Colonnes clés : `type_auteur_diagnostic`, `sous_type_auteur_diagnostic`

## Requête

```sql
SELECT sous_type_auteur_diagnostic, COUNT(DISTINCT id_candidat) as n
FROM public.taux_transformation_prescripteurs
WHERE date_diagnostic >= 'YYYY-01-01' AND date_diagnostic < 'YYYY+1-01-01'
GROUP BY 1 ORDER BY n DESC
```

## Baseline (12 derniers mois)

| Prescripteur | Candidats | % |
|--------------|----------:|--:|
| FT (France Travail) | ~138 000 | 58% |
| ML (Missions Locales) | ~37 000 | 15% |
| DEPT (Départements) | ~15 000 | 6% |
| PLIE | ~12 000 | 5% |
| ODC (Cap emploi) | ~9 000 | 4% |

33 types au total.

## Cards Metabase

- 7059 : candidats accompagnés par prescripteurs habilités
- 7084 : candidats acceptés en IAE sur 3 derniers mois
