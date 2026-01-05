# PASS IAE

*Dernière mise à jour : 2025-01-03*

## Source

Table : `public.pass_agrements_valides`
Colonnes clés : `date_début`, `date_fin`, `id_candidat`, `type_structure`

## Expirations par mois

```sql
SELECT TO_CHAR(date_fin, 'YYYY-MM') as mois, COUNT(*) as n
FROM public.pass_agrements_valides
WHERE date_fin >= 'YYYY-MM-01' AND date_fin < 'YYYY-MM-01'::date + INTERVAL '1 month'
GROUP BY 1 ORDER BY 1
```

## Baseline (12 prochains mois depuis jan 2025)

~6 000 à 12 000 expirations/mois, sauf novembre 2026 (~34 000).

## Autres tables liées

- `pass_iae_et_demandes` : demandes et statuts
- `pass_agréments` : tous les agréments
- `suspensions_pass` : suspensions en cours
