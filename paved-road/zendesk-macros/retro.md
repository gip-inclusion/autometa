# Rétro — zendesk-macros

Parcours joué dans l'ordre cette fois : contrat validé et committé avant la première ligne de code,
vingt rouges journalisés sur les tests seuls, puis le code. Le précédent (`zendesk-write`) a porté
l'essentiel : le moteur de propositions s'est généralisé sans toucher aux tests des articles.

Ce qui a frotté :

- La sonde de l'API a décidé plus de choses que la discussion. Les 304 réponses tiennent chacune sur
  une seule ligne HTML (le diff ligne à ligne des articles aurait réaffiché chaque réponse entière),
  et 266 contiennent des espaces insécables codées : deux critères (`DOD-3`, `DOD-20`) sont nés d'un
  comptage, pas du brief. Le gap-hunter avait vu juste en raisonnant, la sonde l'a chiffré.
- `pytest <fichier>` lancé à la main joue aussi les tests `external` : `pytest.ini` ne les exclut
  pas, seul `make test` le fait. Pendant les cycles, l'aller-retour réel des articles (bac à sable) a
  tourné plusieurs fois, et celui des macros deux fois avant l'accord du demandeur. Rien n'est resté
  dans Zendesk, mais l'écriture n'était pas autorisée. Les commandes de preuve `-k dod_N_` ne
  sélectionnent pas ces tests ; le risque est dans l'itération, pas dans la preuve.
- La lentille lancée sur deux modèles a rendu des résultats complémentaires : un seul a vu le
  bloqueur (valeur d'action en liste), l'autre a vu la transformation qui pouvait écrire un champ non
  montré. Aucun des deux n'aurait suffi seul.
- Un test vert du premier coup était creux : la protection des variables Zendesk était testée avec
  un motif en majuscule sur des variables en minuscules. Rattrapé en retirant la protection pour voir
  le test échouer — geste que le rouge journalisé ne remplace pas, puisque le rouge échouait à
  l'import.
- Le skill porte deux critères à moitié (`DOD-6`, `DOD-10` : validation dans un message ultérieur,
  montrer avant de créer). Comme pour `zendesk-write`, aucun test ne démontre la conduite de
  conversation ; le vert repose sur le code qui l'entoure.

Coût : non mesuré par l'agent (`/cost` n'est pas accessible depuis la session).
