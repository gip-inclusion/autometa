# Lentille design-coherence — 2026-10-23

Deux passes en parallèle (Fable, Opus). Un même bloqueur relevé par les deux, six remarques dont
plusieurs communes. Ce qui en a été fait :

- **Bloqueur, DOD-4 : un démarrage pendant la coupure échoue dès qu'une conversation est à
  débloquer** — corrigé : la récupération de démarrage lit Redis ; si la file est injoignable,
  elle est journalisée et sautée, l'application démarre, et le sweep périodique libère ces
  conversations une fois la file revenue. Démontré par un test qui passe par `startup()` avec une
  conversation à débloquer et une file qui refuse la connexion.
- **Le test DOD-4 passait sur le code d'origine (Fable)** — corrigé : sur une file muette, le code
  d'origine fige au lieu de lever, et une boucle figée paraît vivante. Les tests DOD-4 utilisent
  désormais une file qui refuse la connexion, comme au redémarrage du proxy à 00:12 : l'échec est
  immédiat, sans attente possible. Vérifié : les trois tests de boucle échouent sur le code
  d'origine.
- **`except RedisError` plus large que le critère** — corrigé : seules les erreurs de connexion et
  de délai réinitialisent le client ou sautent la récupération. Une erreur de commande remonte comme
  avant. Une erreur d'authentification est, dans redis-py, une erreur de connexion : elle reste
  attrapée au ping et ressort à la commande suivante, comme avant ce parcours.
- **DOD-1 : la moitié « un message envoyé après le retour reçoit sa réponse » n'est pas testée** —
  conservé : `test_consumer_survives_task_handling_exception` et
  `test_consumer_survives_when_recovery_also_fails` montrent déjà que la boucle sert le message
  suivant après une erreur ; redis-py ferme la connexion fautive sur délai dépassé et en ouvre une
  neuve à la commande suivante (`read_response`, `disconnect_on_error`). Rejouer un retour de
  service dans un test unitaire demanderait un proxy TCP pilotable, pour un comportement de la
  bibliothèque.
- **Pools abandonnés sans fermeture pendant une panne** — conservé : c'est le comportement que la
  fonction visait déjà et que la mauvaise exception empêchait. Les boucles gardent leur client ;
  fermer l'ancien pool sous leurs pieds casserait leurs connexions. Le ramasse-miettes les récupère.
- **`socket_timeout` fixe aussi le délai de connexion** — conservé : c'est voulu, la coupure du
  2026-10-22 bloquait aussi à la connexion (authentification sans réponse).
- **Effets sur une file saine** — vérifiés par les deux passes : neutres. La seule lecture longue
  du pool est le BLPOP (1 s côté serveur) ; le flux à l'écran lit avec son propre délai ; l'écoute
  de l'arrêt se réveille une fois par seconde, sans effet visible.

Seconde passe (Fable, Opus), 2026-10-23 : aucun bloqueur. Les réponses de la première passe
tiennent ; la reprise après retour du service (DOD-1), justifiée en mots, a été vérifiée par sonde
(proxy TCP) : le client du pool sert le message suivant dès que la file répond. Trois remarques :

- **Les conversations à débloquer au démarrage attendent le sweep, passé ses 15 minutes, avec la
  note « tâche bloquée »** — le commentaire du code le dit désormais ; même cas que le message
  envoyé pendant une coupure, écarté par la DoD.
- **La libération écrit la base avant de notifier l'écran et d'effacer la clé `running:`** —
  conservé : ordre antérieur à ce parcours, la clé expire seule en 300 s.
- **`engine_limits.main()` reste sans délai** — conservé : outil opérateur en ligne de commande,
  hors DOD-3.
