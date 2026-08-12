---
title: Suggérer des tags pour les objets non tagués
schedule: weekly
timeout: 1800
---

Propose des tags à partir du vocabulaire synchronisé et écrit le résultat dans `dashboard_storage.tag_suggestions`. **N'applique rien** : les suggestions sont relues avant d'être posées. Le même jeu sert d'évaluation du vocabulaire (termes jamais choisis, termes confondus) et de corpus d'exemples pour le tagueur automatique. Voir `lib.tag_suggestions.run`.

Le corpus est parcouru **par tranches** : chaque passe ignore les objets déjà suggérés et s'arrête sur un budget de temps, les objets restants étant repris à la passe suivante. Les tableaux de bord passent en premier, puis les rapports, puis les conversations — de loin les plus nombreuses. Les termes encore « proposés » (créés depuis l'application, pas encore promus dans Notion) sont exclus du vocabulaire soumis au modèle.
