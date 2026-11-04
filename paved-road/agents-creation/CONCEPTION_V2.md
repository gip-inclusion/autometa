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
l'agent chercher dans le dépôt, et les préparations ne tournent jamais dans le conteneur web.

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

## Préparations (les crons précèdent l'agent)

Liste fermée `config/agent_preparations.yaml` : chaque préparation nomme une tâche existante du
dossier `cron/`. Une nouvelle préparation se déclare par une PR (une tâche dans `cron/`, une
ligne dans la liste). Une configuration en cite jusqu'à trois, dans l'ordre. Avant chaque run,
Autometa les exécute dans cet ordre avec le moteur des crons (`web.cron.execute_task`, donc
timeout, `cron_runs` et page `/cron` habituels), publie leurs sorties sur S3 comme
`publish_dataset` et passe l'URL au run (`input_uri`). Une préparation en échec : pas de run.

## Cycle de vie : stop and go

Un run est un conteneur Scaleway jetable qui va au bout puis disparaît. Un agent « permanent »
n'est pas un processus allumé : c'est un déclenchement périodique (préparations, puis run).
`autometa-jobs` n'expose aucun déclenchement sur horaire (`lib/jobs.py` : créer, déclencher,
lire), donc c'est Autometa qui déclenche. La configuration porte une `cadence` (quotidienne,
hebdomadaire, mensuelle, ou absente pour un agent à la demande) ; une tâche `cron/agents` du lot
`maintenance` lance chaque matin les agents dus et livre les runs terminés depuis la veille.
Depuis le chat, `lancer` démarre un conteneur one-off Scalingo, comme le run manuel d'un cron :
jamais dans le processus web.

## Limites connues

- Les crons existants sont des synchronisations : leur sortie est un compte rendu, pas un jeu de
  données. Une préparation utile à un agent sera le plus souvent une tâche nouvelle de `cron/`.
- Un run lancé le matin est livré au passage suivant de `cron/agents`, ou à la demande.
