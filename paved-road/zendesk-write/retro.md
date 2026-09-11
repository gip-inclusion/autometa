# Rétro — zendesk-write

Ce parcours a été joué **après coup** sur un développement déjà écrit : le code existait en un commit
quand le demandeur a proposé de tester le parcours. Le contrat reprend les décisions prises en
conversation avant la première ligne, mais l'historique a été réordonné (contrat, puis code) pour
satisfaire le contrôle d'antériorité, et les rouges ont été rejoués en retirant le code de l'arbre
de travail. Le contrôle dit lui-même qu'une réécriture le contourne : ici, elle a été annoncée et
acceptée comme la décision 5 du contrat.

Ce qui a frotté :

- Le parcours vit dans un plugin chargé par `make claude` seulement. Lancé à la main, rien ne le
  propose, et l'agent a démarré hors parcours sans s'en rendre compte. Les commandes `make` restent
  utilisables sans le plugin ; les sous-agents (`gap-hunter`, `design-coherence`) ont été rejoués
  avec leur brief copié dans un agent générique.
- Le worktree a été supprimé du disque en cours de route par une autre session ; le code a été
  récupéré depuis le reflog. Un commit refusé par le hook suivi d'un `reset --hard` a perdu quatre
  fichiers indexés, récupérés depuis les objets git détachés. Deux incidents, aucun lié au parcours.
- `main` a avancé deux fois pendant le parcours. La deuxième fois, le contrôle de qualité des tests a
  refusé un test que la branche n'avait pas touché, parce qu'il compare à `origin/main` : le
  message ne dit pas « rebase », il dit « assertion retirée ». Un rebase a suffi.
- `make paved-road-checks CHECK=doctor` n'existe pas, alors que `advance` parle de `doctor` ;
  c'est `make doctor`.
- Le vert d'un critère porté par un `SKILL.md` (`DOD-3`, `DOD-8`) repose sur le code qui l'entoure,
  pas sur la règle de conversation elle-même : la lentille a vérifié que le skill le dit, aucun
  test ne le démontre.
- La branche avait été poussée à 15:15 par une action hors de cette session ; après le
  réordonnancement, l'agent ne peut plus pousser sans forcer, ce qui lui est interdit.

Coût : non mesuré par l'agent (`/cost` n'est pas accessible depuis la session).
