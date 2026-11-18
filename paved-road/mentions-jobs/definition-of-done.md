# Mentionner un job dans le chat

## Ce que je veux

Dans une conversation, pouvoir citer un job existant de la page Jobs pour en parler avec l'agent :
qu'il sache ce que fait ce job, comment se sont passés ses derniers runs et ce qu'a produit le
dernier, et qu'il propose de le relancer sans jamais le relancer sans mon accord.

## Ce qui devra marcher

DOD-1 — Quand j'écris `@nom-du-job` dans un message, alors l'agent reçoit, en plus de mon message,
  la consigne du job, ses derniers runs (statut, date) et un extrait de la dernière sortie réussie.

DOD-2 — Le contexte ajouté pour un job reste borné : une consigne ou une sortie très longue est
  tronquée, et il est signalé comme tronqué ; au plus trois jobs sont pris en compte par message.

DOD-3 — Quand je mentionne un nom qui ne correspond à aucun job, ou que le service de jobs ne
  répond pas, alors mon message part quand même, tel que je l'ai écrit, sans erreur.

DOD-4 — Mentionner un job ne lance aucun run ; le contexte transmis à l'agent lui demande de
  proposer la relance et de ne la faire qu'après un « oui » explicite. Après ce oui, l'agent
  relance le job existant, sans en créer un nouveau.

DOD-5 — Quand je tape `@` dans la zone de saisie, une liste des jobs dont le nom commence par ce
  que j'ai tapé s'affiche ; en choisir un complète la mention.

## Sources lues

- `web/routes/conversations.py:send_message` — le contexte d'une conversation « knowledge » est
  déjà préfixé au prompt envoyé au runner, sans toucher au message enregistré : la mention de job
  réutilise ce point d'entrée.
- `lib/jobs.py`, `web/routes/jobs.py`, `tests/test_jobs_routes.py` — client HTTP du service de jobs
  externe et façon de le simuler en test (`mocker.patch` sur `lib.jobs`).
- `skills/compose_and_launch_job/` — la règle de confirmation explicite avant tout lancement ; le
  script ne sait que créer un nouveau pipeline, d'où la relance d'un job existant de `DOD-4`.
- `gates.toml`, `scripts/check_route_auth.py` — la route d'autocomplétion de `DOD-5` naît avec
  une dépendance d'authentification.

## Questions ouvertes

Aucune.

## Validation

En attente de validation par Alexis Akinyemi. Défauts retenus : syntaxe `@nom` exact du pipeline,
trois jobs au plus par message, trois derniers runs, extrait de sortie limité à 3 000 caractères.
