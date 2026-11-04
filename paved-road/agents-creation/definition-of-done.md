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

## Questions ouvertes

Aucune.

## Validation

En attente de validation par Alexis Akinyemi. Défauts retenus : identifiant du job
`agent-<slug>` en attendant le tag de la PR 1 ; un identifiant d'agent ne se réutilise pas, même
retiré ; le job retiré reste dans le moteur de jobs, faute d'API de suppression ; la livraison
d'un run se déclenche à la demande, pas automatiquement à la fin du run.
