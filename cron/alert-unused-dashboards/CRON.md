---
title: Alerter sur les tableaux de bord sans visite depuis 60 jours
schedule: daily
timeout: 300
batch: maintenance
---

Poste chaque matin dans le canal d'alerte la liste des tableaux de bord non archivés, créés il y a
plus de 60 jours, qu'aucune visite Matomo n'a ouverts sur les 60 derniers jours, vue interne ou
publique. Chaque ligne donne le propriétaire et le lien vers la fiche, où l'archiver. La liste est
recalculée chaque jour : un tableau y reste jusqu'à son archivage.

Les visites sont lues jour par jour : sur une semaine, un mois ou une plage, Matomo regroupe les
pages les moins vues, et un tableau réellement consulté passerait pour inutilisé. Si Matomo ne
répond pas en entier, rien n'est posté et la tâche échoue.
