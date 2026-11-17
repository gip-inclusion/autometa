# Rétro — redis-timeouts

Parcours mené à la main depuis une session ordinaire : le plugin n'est chargé que par `make claude`,
et la demande est venue en cours de diagnostic d'incident. Les fichiers d'étape se suivent bien
sans lui ; les deux lentilles ont été lancées comme sous-agents de lecture avec leur définition en
consigne.

Ce qui a payé : les lentilles. La chasse aux trous a trouvé `DOD-4` (boucles de fond tuées par leur
premier appel si la file est coupée au démarrage), absent du brief et du diagnostic. La revue l'a
trouvé incomplet (la récupération de démarrage tombait encore), et Fable a vu que le premier test
de `DOD-4` passait sur le code d'origine — une file muette fige au lieu de lever, et une boucle
figée paraît vivante. Sans ces trois passes, le contrat aurait été « démontré » sur un trou.

Ce qui a frotté :

- Le rouge de `DOD-1` ne dit que « la constante de délai n'existe pas » : le test règle le délai à
  0,2 s pour rester rapide, et ce réglage échoue avant le code. Le vrai figement a été reproduit à
  part, sur le code d'origine, par un script jetable hors dépôt. Un rouge qui échoue sur un
  attribut absent passe `advance` sans rien démontrer du comportement.
- `fakeredis.TcpFakeServer` laisse des fils d'exécution qui tournent sans fin après `shutdown()`
  (lecture non bloquante en boucle sur `time.sleep(0)`) ; ils ont fait échouer un test sans rapport
  qui espionne `time.sleep`. Le test de `DOD-2` est passé en intégration sur un vrai Redis, et le
  rouge a été rejoué avec la nouvelle commande.
- `test_execute_task_alerts_slack_with_stderr_rather_than_stdout` a échoué une fois sous la charge
  de la suite complète, puis passé au commit suivant sans changement : instable, à surveiller.
- Le contrôle de qualité des tests a refusé un test sans assertion (« démarre sans lever »), à
  raison.

Coût : non mesuré, `/cost` n'est pas accessible depuis cette session.
