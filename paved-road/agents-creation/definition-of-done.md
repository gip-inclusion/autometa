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
  celui d'un agent retiré, ne donne aucune proposition, et Autometa me dit pourquoi. L'identifiant
  d'un agent actif donne une proposition de modification (`DOD-13`).

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
  agent peut utiliser (destinations, sous-agents et leurs modèles, préparations, cadences), même
  quand aucune destination n'a de cible configurée sur l'instance, et la conversation ne plante
  pas. Si le conteneur tue malgré tout le CLI, le message dit « tué par le système (signal N),
  probablement faute de mémoire » et le journal consigne la mémoire du conteneur à ce moment.

DOD-10 — Un agent peut déclarer jusqu'à trois sous-agents Ollama Cloud, de trois types fermés :
  classificateur (question oui/non et seuil), extraction (champs d'un schéma déclaré), résumé
  (longueur maximale). Chaque type a sa liste fermée de modèles ; un type ou un modèle hors liste,
  un schéma mal formé ou une longueur absurde sont refusés comme une destination hors liste.
  Après le run, avant la livraison, Autometa les applique avec sa propre clé à chaque production,
  dans l'ordre de la configuration. Un classificateur sous le seuil arrête la chaîne : la
  production n'est pas livrée mais reste enregistrée avec sa probabilité. Un sous-agent en échec :
  rien de cette production n'est livré, elle est tracée en échec et réessayée au passage suivant.
  Les journaux ne portent aucun contenu ; la trace du run compte les appels aux sous-agents.

DOD-11 — Un agent peut déclarer jusqu'à trois préparations, d'un des trois types fermés
  (requête d'une base Notion, jeu de données S3, dernière sortie réussie d'une tâche existante de
  `cron/`). Avant chaque run, leurs contenus sont rassemblés dans l'ordre déclaré et transmis au
  run ; une préparation sans contenu empêche le run. Ni l'agent ni le worker ne lancent de cron.

DOD-12 — Aucun agent n'a de cron à lui : un seul cron générique, dans un lot existant, livre
  chaque jour les runs terminés des agents actifs puis lance ceux dont la cadence tombe. Un agent
  en échec n'empêche pas les autres.

DOD-13 — Depuis le chat, lire est libre ; lancer un run maintenant et modifier un agent
  (configuration, consigne, cadence) ne se font qu'après mon oui dans un message ultérieur,
  vérifié par le code, et une confirmation ne sert qu'une fois. Une modification se défait et
  rend ce qu'elle remplaçait. Passer une destination en réel reste une PR.

DOD-14 — Le parcours « guide-moi pour créer un agent avec un classificateur et deux crons » va au
  bout : proposition complète, rien avant mon oui dans un message suivant, création, lancement
  après un autre oui, sorties des deux crons dans l'ordre transmises au run, classificateur puis
  résumé sur la sortie, livraison selon le mode (ombre par défaut).

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
  `noul`, réponse : la probabilité du oui (`DOD-10`). `web/llm.py` lit déjà `OLLAMA_API_KEY` et
  appelle Ollama par son API native ; extraction et résumé passent par `/api/chat` (sortie
  contrainte par `format` pour l'extraction). Noms des modèles relevés le 05/11 dans
  `https://ollama.com/api/tags` : `clef:27b`, `glm-5.2`, `gemma4:31b`.
- `scalingo.json`, `scripts/review_app.py`, doc Scalingo des review apps (une review app clone la
  formation de l'application parente, `scalingo.json` l'emporte) et client Go de Scalingo
  (`containers: [{name, amount, size}]`) ; mesures locales du CLI dans
  `paved-road/agents-creation/CONCEPTION_V2.md` (`DOD-9`).
- `web/cron.py`, `lib/job_inputs.py`, `lib/notion.py` — `cron_runs` (dernière sortie d'une
  tâche), `publish_dataset` (S3, URL présignée) et `query_database` réutilisés pour `DOD-11` ;
  le lot `maintenance` et `is_due` pour `DOD-12`. `lib/jobs.py` n'a ni déclenchement sur horaire
  ni mise à jour de pipeline : c'est Autometa qui déclenche, et une consigne changée est un
  pipeline nouveau (`DOD-13`).
- `paved-road/agents-creation/CONCEPTION_V2.md` — la conception de `DOD-9` à `DOD-14`.

## Questions ouvertes

Aucune.

## Validation

En attente de validation par Alexis Akinyemi. Défauts retenus : identifiant du job
`agent-<slug>` en attendant le tag de la PR 1 ; un identifiant d'agent ne se réutilise pas, même
retiré ; le job retiré reste dans le moteur de jobs, faute d'API de suppression ; la livraison
d'un run se déclenche à la demande, ou au passage quotidien suivant pour un agent qui a une
cadence. Ajouté le 04/11 à la demande d'Alexis : classificateur, préparations, cadence
(`DOD-9` à `DOD-14`), le cerveau du worker restant hors périmètre ; la relance de #276
devra réutiliser la confirmation de `DOD-13`. Étendu le 05/11 à la demande d'Alexis : sous-agents
extraction et résumé, chaînés dans l'ordre (`DOD-10`, `DOD-14`), et trace lisible d'un CLI tué
par le système (`DOD-9`).
