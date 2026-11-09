# Autometa ne reste plus muet après une coupure de sa file d'attente

## Ce que je veux

Le 22 octobre, une coupure de 19 minutes du service qui transmet les messages à l'agent a laissé
Autometa sans réponse pendant quinze heures, jusqu'à un redémarrage manuel. Une coupure de ce
service doit coûter la durée de la coupure, pas une nuit : Autometa doit reprendre seul dès que le
service revient.

## Ce qui devra marcher

DOD-1 — [du brief : « the redis timeout fix »] Quand la file d'attente accepte la connexion mais ne
  répond plus, Autometa s'en aperçoit en quelques secondes au lieu d'attendre indéfiniment, et
  continue d'essayer : un message envoyé après le retour du service reçoit sa réponse, sans
  redémarrage.

DOD-2 — [du brief : « the redis timeout fix »] Le signal d'arrêt diffusé par la file interrompt
  toujours une réponse en cours, même après plusieurs minutes de silence sur la conversation, quel
  que soit le processus du serveur qui la traite.

DOD-3 — [du brief : « the redis timeout fix »] Quand la file d'attente ne répond plus, le titre et
  les étiquettes d'une nouvelle conversation sont tout de même générés, après quelques secondes
  d'attente au plus.

DOD-4 — [du brief : « enforce product health »] Si Autometa démarre pendant une
  coupure de la file, il reprend seul dès le retour du service : un message envoyé ensuite reçoit
  sa réponse, sans second redémarrage.

## Sources lues

- `web/redis_conn.py` — **R1** : le client partagé est créé sans aucun délai de lecture ni de
  connexion ; une lecture sur une connexion morte attend donc sans fin.
- `web/runner.py` — **R1** : la boucle qui distribue les messages attend la file avec un délai
  côté serveur d'une seconde et ne garde qu'un client ; elle rattrape les erreurs mais pas une
  attente sans fin, d'où `DOD-1`. L'écoute du bouton d'arrêt reste en lecture bloquante pendant
  toute la réponse : avec un délai de lecture, elle tomberait au premier silence, d'où `DOD-2`.
  L'arrêt demandé au processus qui traite la réponse agit sans passer par la file : seule la
  diffusion vers un autre processus en dépend, c'est elle que vise `DOD-2`. Les trois boucles de
  fond obtiennent leur client hors de leur rattrapage d'erreur, et ce premier appel vérifie la
  connexion : si la file est coupée au démarrage, elles meurent sans bruit, d'où `DOD-4`.
- `web/routes/conversations.py` — **R1** : le flux affiché à l'écran lit déjà avec son propre
  délai court ; il n'est pas affecté.
- Inventaire de tous les appels Redis de `web/`, `lib/`, `cron/`, `scripts/` et `skills/` —
  **R1** : seules deux lectures attendent longtemps, l'attente de la file (délai serveur d'une
  seconde) et l'écoute de l'arrêt (`DOD-2`) ; le flux à l'écran fixe son propre délai (3 s) ;
  `web/routes/sources.py`, `web/selftest.py` et `scripts/doctor.py` n'envoient que des commandes
  brèves. Rien d'autre ne change de comportement quand la file répond.
- `web/engine_limits.py`, `web/llm.py` — **R1** : la vérification de limite faite avant chaque
  titre ou étiquette ouvre son propre client, lui aussi sans délai, d'où `DOD-3`.
- redis-py 7.4 installé, `redis/asyncio/client.py` et `redis/asyncio/connection.py` — **R1** : une
  lecture bloquante de l'abonnement retombe sur le délai de lecture du client ; une lecture avec
  délai explicite rend « rien » sans erreur.
- Incident du 2026-10-22 — **R2** : coupure de 19:43:02 à 20:02:19 (journaux du service Redis,
  `scalingo logs --addon`), dernière réponse de l'agent à 18:57:03 et reprise à 10:52:48 le
  lendemain après redémarrage (base de production, table `messages`), 9 conversations en attente
  libérées au redémarrage (journaux applicatifs Datadog, « Cleared 9 stuck conversations »), et
  silence de la boucle de distribution à partir de 20:02:20 alors que les autres boucles
  reprenaient (Datadog, portée `web.runner`).
- `docs/plans/`, DoD des parcours précédents — **R5** : aucun ne traite des délais Redis. Le
  parcours `runner-cleanup` (branche non fusionnée) traite le nettoyage en fin de réponse, pas
  l'attente sans fin.

Aucun terme IAE, aucun tableau de bord, aucun usage à mesurer : **R3**, **R4** et **R6** ne se
déclenchent pas.

## Questions ouvertes

Aucune.

Écarté de ce parcours, avec la raison :

- relancer la boucle de distribution si elle cesse de tourner pour une autre cause : filet
  supplémentaire, parcours à part.

Propositions de la lentille gap-hunter écartées, avec la raison :

- un message envoyé pendant la coupure libère aussitôt la conversation avec une invitation à
  réessayer, au lieu de la laisser bloquée quinze minutes : comportement antérieur aux délais, qui
  vaut pour toute panne de la file ; parcours à part ;
- une réponse en cours au moment de la coupure va à son terme au lieu d'être interrompue avec un
  message d'erreur : même raison. Les délais n'aggravent rien : une connexion fermée lève déjà
  aujourd'hui, une connexion muette figeait la réponse sans fin.

## Validation

Validé par LJ le 2026-10-23, avec une consigne : ne rien casser d'autre.

Deux défauts soumis et retenus : un message envoyé pendant une coupure et une réponse en cours au
moment d'une coupure relèvent d'un parcours à part.
