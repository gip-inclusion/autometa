# Créer un agent depuis une conversation, seulement après ma confirmation

## Ce que je veux

Pouvoir demander à Autometa, dans une conversation, de créer un agent : un job qui traite des
données et dépose ce qu'il produit dans Slack ou Notion. Autometa me montre d'abord ce qu'il va
créer, et rien n'existe tant que je n'ai pas dit oui dans un message suivant. Je dois pouvoir
retirer l'agent ensuite.

## Ce qui devra marcher

DOD-1 — Quand Autometa propose un agent, il me présente sa configuration (titre, mission,
  destinations et leur mode) et la consigne du job, et aucun job n'est encore créé.

DOD-2 — Une configuration refusée par le validateur `pdi.agent/1`, ou dont l'identifiant est
  déjà pris par un agent, ne donne aucune proposition, et Autometa me dit pourquoi.

DOD-3 — L'agent n'est créé que si je l'approuve dans un message ultérieur de la même
  conversation : approuver dans le tour même de la proposition, depuis une autre conversation ou
  hors conversation est refusé et ne crée rien. Une proposition que je ne valide pas reste sans
  effet, indéfiniment.

DOD-4 — Quand j'approuve, un job nommé `agent-<identifiant>` est créé dans le moteur de jobs, sa
  consigne porte le contrat de sortie qui liste ses seules destinations, et l'agent garde trace
  de qui l'a approuvé.

DOD-5 — Approuver une seconde fois une proposition déjà appliquée ne crée rien : Autometa me dit
  dans quel état elle est.

DOD-6 — Après création, je peux retirer l'agent : ses runs ne sont plus livrés nulle part.
  Retirer une proposition jamais appliquée, ou déjà retirée, ne change rien et me dit son état.

DOD-7 — Livrer un run d'un agent n'accepte qu'un run terminé de son propre job, et passe sa
  sortie par la livraison de `agents-ecriture` (liste fermée, modes).

DOD-8 — Une production en relecture ne s'écrit que si je l'approuve dans un message ultérieur à
  celui où Autometa me l'a montrée, dans la même conversation.

DOD-9 — Quand je demande à Autometa de me guider pour créer un agent, il me présente ce qu'un
  agent peut utiliser (destinations, modèles, préparations, cadences), même quand aucune
  destination n'a de cible configurée sur l'instance, et la conversation ne plante pas.

DOD-10 — Un agent peut déclarer un classificateur pris dans une liste fermée de modèles, avec une
  question oui/non et un seuil ; un modèle hors liste est refusé comme une destination hors liste.
  Après le run, Autometa pose la question à chaque production avec sa propre clé : une
  production sous le seuil n'est pas livrée mais reste enregistrée avec sa probabilité, et sans
  réponse du classificateur rien n'est livré pour cette production.

DOD-11 — Un agent peut déclarer jusqu'à trois préparations, prises dans une liste fermée de
  tâches du dossier `cron/`. Avant chaque run, elles tournent dans l'ordre déclaré, et leurs
  sorties sont transmises au run ; si l'une échoue ou manque, le run n'est pas lancé. Le worker ne
  lance jamais de cron.

DOD-12 — Un agent est déclenché, pas allumé : avec une cadence, Autometa livre chaque jour ses
  runs terminés puis lance ceux qui sont dus ; depuis le chat, le lancement part dans un
  conteneur dédié, jamais dans le processus web. Un agent en échec n'empêche pas les autres.

DOD-13 — Le parcours « guide-moi pour créer un agent avec un classificateur et deux crons » va au
  bout : proposition complète, rien avant mon oui dans un message suivant, création, deux
  préparations dans l'ordre avant le run, classificateur sur la sortie, livraison selon le mode
  (ombre par défaut).

## Sources lues

- `lib/zendesk_changeset.py`, `skills/zendesk/SKILL.md`, `paved-road/zendesk-write/` — patron
  plan / apply / revert sur S3 sans table, états `planned`, `applied`, `reverted`, refus d'un
  état inattendu : repris pour `DOD-1`, `DOD-5` et `DOD-6`. La règle « jamais `apply` dans le tour
  du `plan` » n'y est qu'une consigne du skill ; ici elle est vérifiée par le code (`DOD-3`).
- `web/agents/cli.py`, `web/config.py` — le CLI de l'agent reçoit `AUTOMETA_CONVERSATION_ID` et
  `AUTOMETA_USER_EMAIL` : ils permettent de vérifier qu'un nouveau message de l'utilisateur est
  arrivé après la proposition (`DOD-3`, `DOD-8`) et de nommer qui a approuvé (`DOD-4`).
- `lib/jobs.py`, `skills/compose_and_launch_job/` — création d'un pipeline et format de sortie
  `json` ; le service de jobs n'expose aucune suppression de pipeline, d'où le retrait côté
  Autometa (`DOD-6`). Le moteur de jobs est simulé dans les tests.
- `paved-road/agents-ecriture/` — la livraison réutilisée par `DOD-7` et `DOD-8`.
- `web/agents/cli.py`, `web/runner.py` — Autometa ne tue le CLI que sur annulation, budget
  d'appels ou arrêt ; un « code -9 » sans autre trace vient de l'extérieur (`DOD-9`).
- ollama.com/library/clef — `clef` sur Ollama Cloud, point d'entrée `/v1/systemone`, question
  `noul`, réponse : la probabilité du oui (`DOD-10`). `web/llm.py` lit déjà `OLLAMA_API_KEY`.
- `web/cron.py`, `lib/job_inputs.py` — `execute_task` (timeout, `cron_runs`) et
  `publish_dataset` (S3, URL présignée) réutilisés pour `DOD-11` ; `web/scalingo.py`, le
  conteneur one-off du run manuel des crons, pour `DOD-12`. `lib/jobs.py` n'a aucun déclenchement
  sur horaire : c'est Autometa qui déclenche.
- `paved-road/agents-creation/CONCEPTION_V2.md` — la conception de `DOD-9` à `DOD-13`.

## Questions ouvertes

Aucune.

## Validation

En attente de validation par Alexis Akinyemi. Défauts retenus : identifiant du job
`agent-<slug>` en attendant le tag de la PR 1 ; un identifiant d'agent ne se réutilise pas, même
retiré ; le job retiré reste dans le moteur de jobs, faute d'API de suppression ; la livraison
d'un run se déclenche à la demande, ou au passage quotidien suivant pour un agent qui a une
cadence. Ajouté le 04/11 à la demande d'Alexis : classificateur, préparations, cadence
(`DOD-9` à `DOD-13`), le cerveau du worker restant hors périmètre.
