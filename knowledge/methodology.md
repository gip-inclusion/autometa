# Méthodologie d'analyse

Principes à respecter pour toutes les analyses de données, quelle que soit la source
(Metabase Stats, Metabase Datalake, Matomo, etc.).

## Données temporelles

### Choix de la date de référence

Les événements métier ont souvent plusieurs dates associées. **Toujours clarifier 
avec l'utilisateur quelle date utiliser** car les résultats peuvent différer significativement.

| Service | Dates possibles | Écart typique |
|---------|-----------------|---------------|
| Emplois (candidatures) | Date candidature vs date embauche | 30+ jours |
| RDV-Insertion | Date prise de RDV vs date du RDV vs date de présence | Variable |
| Marché | Date demande vs date mise en relation | Variable |

**Action :** Poser la question systématiquement avant toute analyse temporelle.

### Comparabilité des taux dans le temps

Les taux basés sur des événements différés (réponse, embauche, conversion) sont **biaisés 
par l'ancienneté** : les données anciennes ont eu plus de temps pour atteindre l'état final.

**Bonne pratique :** Utiliser une **fenêtre fixe** pour rendre les taux comparables.

Exemple : "Taux de candidatures validées **en moins de 30 jours**"
- ✅ Exclure les candidatures de moins de 30 jours (pas encore comparables)
- ✅ Appliquer la même fenêtre à toutes les périodes

```sql
-- Taux de validation à 30 jours (comparable dans le temps)
SELECT 
    DATE_TRUNC('month', date_candidature) as mois,
    COUNT(*) FILTER (WHERE statut = 'validée' 
                     AND date_validation - date_candidature <= 30) * 100.0 
    / COUNT(*) as taux_validation_30j
FROM candidatures
WHERE date_candidature < CURRENT_DATE - INTERVAL '30 days'
GROUP BY 1
