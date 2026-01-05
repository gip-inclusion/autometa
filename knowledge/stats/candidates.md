# Candidats avec diagnostic

*Dernière mise à jour : 2025-01-03*

## Source

Table : `public.taux_transformation_prescripteurs`
Colonnes clés : `id_candidat`, `date_diagnostic`, `diagnostic_valide`

## Requête

```sql
SELECT COUNT(DISTINCT id_candidat)
FROM public.taux_transformation_prescripteurs
WHERE date_diagnostic >= 'YYYY-01-01' AND date_diagnostic < 'YYYY+1-01-01'
```

## Baseline (12 derniers mois)

~237 000 candidats

## Cards Metabase

- 7087 : diagnostics valides par mois
- 7088 : diagnostics non valides par mois
