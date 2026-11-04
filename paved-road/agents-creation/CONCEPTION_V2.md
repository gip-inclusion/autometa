# Agents, version 2 : classificateur, préparations, cadence

Révision de #278 demandée par Alexis le 04/11, après test en review app. Le brief cite
`paved-road/agents-confirmation/` ; le contrat de #278 vit dans `paved-road/agents-creation/`,
gardé tel quel pour ne pas déplacer un contrat déjà relu.

## Le plantage « code -9 »

Le message « Process exited with code -9: » sans stderr veut dire que le processus du CLI
Claude a été tué de l'extérieur. Autometa ne tue le CLI que sur annulation, budget d'appels ou
arrêt, et ces trois chemins laissent une autre trace (« Interrompu », message de budget, aucun
message). Les commandes que l'agent pouvait lancer pour « vérifier les destinations » coûtent
moins de 100 Mo et ne plantent pas avec des variables vides. La cause la plus probable est la
limite mémoire du conteneur de la review app (le CLI pèse 200 à 300 Mo à lui seul). Elle ne se
voit pas en local. Ce que cette PR change : le skill a une commande `destinations` qui répond
tout de suite (destinations, modèles, préparations, cible configurée ou non), au lieu de laisser
l'agent chercher dans le dépôt, et rien de lourd ne tourne dans le conteneur web.

## Ce qui reste séparé

- **Le cerveau du worker** (le modèle du conteneur jetable) : hors de cette PR. Il est fixé par
  l'orchestrateur externe `autometa-jobs`, qui ne prend aujourd'hui ni modèle ni clé par pipeline.
- **Les crons et le worker** : le worker ne lance jamais de cron et ne détient aucune clé.

## Classificateur (option a, après le run)

Liste fermée `config/agent_modeles.yaml`, comme les destinations. Une configuration d'agent
déclare `outils_modeles` : un identifiant de la liste, une question oui/non, un seuil. Quand un
run est livré, Autometa pose la question à chaque production avec `clef` sur Ollama Cloud
(`/v1/systemone`, question `noul`, réponse : probabilité du oui), avec sa propre clé
`OLLAMA_API_KEY`. Une production sous le seuil n'est pas livrée, quel que soit son mode, mais
reste enregistrée avec sa probabilité (statut `ecarte`). Sans clé, la livraison est refusée et
rien n'est livré : on ne livre pas sans le filtre demandé.

## Préparations : ce qui nourrit le run

Pas de cron par agent. Les « crons qui alimentent » deviennent des préparations déclarées dans la
configuration de l'agent, de trois types fermés, jusqu'à trois, dans l'ordre :

- `notion` : les lignes d'une base Notion (celles que l'intégration d'Autometa peut lire) ;
- `s3` : un jeu publié par `publish_dataset`, transmis au run par son URL ;
- `cron` : la dernière sortie réussie d'une tâche existante de `cron/`, lue dans `cron_runs`.
  La tâche n'est jamais relancée par l'agent : elle garde son propre horaire.

Avant chaque run, Autometa rassemble ces contenus dans l'ordre, les publie sur S3 comme
`publish_dataset` et passe l'URL au run (`input_uri`). Une préparation sans contenu : pas de run.
Le worker ne lance jamais de cron. Rien de lourd ne tourne : une requête Notion, une lecture en
base, une URL présignée.

## Cycle de vie : stop and go, un seul cron générique

Un run est un conteneur Scaleway jetable qui va au bout puis disparaît. Un agent « permanent »
n'est pas un processus allumé : c'est un déclenchement périodique. Vérifié dans le client
d'Autometa (`lib/jobs.py` : créer, déclencher, lire, annuler) : `autometa-jobs` n'expose aucun
déclenchement sur horaire, ni aucune mise à jour de pipeline. Son code n'est pas dans ce dépôt
et n'a pas pu être lu ; si un déclenchement sur horaire y existe, il pourra remplacer la partie
« run » du cron générique. En attendant, c'est Autometa qui déclenche, par un seul cron
générique, `run-agents`, dans le lot existant `maintenance` (une fois par jour, comme tous les
lots de `cron.json`) : pour chaque agent actif, il livre ses runs terminés, puis, si sa
`cadence` tombe, enchaîne préparations, run, et au passage suivant classificateur et livraison.
Il hérite de `cron_runs`, de Sentry et des alertes Slack des crons.

## Grille d'actions

| Action | Garde |
|---|---|
| lire (configuration, runs, envois) | aucune |
| lancer un run maintenant | confirmation vérifiée par le code, dans un message ultérieur, utilisable une fois |
| modifier la configuration (mission, destinations, préparations, cadence, classificateur, consigne) | plan / apply / revert, même confirmation |
| passer une destination en réel | jamais depuis le chat : PR sur `reel_autorise` |

Une modification se propose avec le même identifiant d'agent. Le moteur de jobs ne met pas à
jour un pipeline : une consigne changée crée un pipeline `agent-<slug>-v<n>`, l'ancien reste.
`retirer` une modification rend ce qu'elle remplaçait ; une proposition devenue obsolète (l'agent
a changé depuis) est refusée.

Hors de cette PR : la relance de #276 (mentions `@job` dans le chat) devra réutiliser cette
confirmation vérifiée par le code au lieu de la seule consigne donnée au modèle, pour que la
mention ne donne aucun pouvoir de plus que le parcours de création.

## Limites connues

- Les lots tournent une fois par jour : une cadence plus fine demanderait un lot de plus dans
  `cron.json`, hors de cette PR.
- Un run lancé le matin est livré au passage suivant de `run-agents`, ou à la demande (`livrer`).
- Comment le worker lit `input_uri` dépend d'`autometa-jobs`, non vérifié.
