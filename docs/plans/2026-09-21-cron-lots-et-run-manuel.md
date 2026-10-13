# Lots de cron et run manuel — design

Ferme les constats **F10** (chaîne série non bornée, lot fourre-tout) et **F13** (double découverte,
run manuel qui bloque le process web) de `docs/audits/2026-09-16-cron-jobs.md`.

## Contexte

Un lot est une ligne de `cron.json`, donc un conteneur Scalingo éphémère qui exécute ses tâches en
série puis s'éteint. Scalingo plafonne `cron.json` à **cinq lignes** ; la limite est relevable sur
demande au support, mais ce design en utilise quatre.

Deux propriétés du lot `default` posent problème. Il est le **fourre-tout** : toute tâche qui ne
déclare rien y atterrit, tableaux de bord compris, dont le nombre grandit à chaque création. Et
personne ne borne sa durée : 49 minutes de timeouts cumulés déclarés, et 36 à 53 minutes pour les
seuls tableaux de bord et publications les jours où le lot est allé au bout (du 05 au 13/09). Depuis
le 14/09 le conteneur est tué presque chaque jour avant la fin (F22 de l'audit), sans rien qui le
signale.

Par ailleurs `POST /api/cron/{slug}/run` exécute la tâche **dans le handler HTTP**, alors que
l'application tourne en uvicorn mono-worker : un run manuel à 600 s de timeout rend le site
indisponible pendant dix minutes. La même route déclenche deux découvertes complètes (listage S3
plus requêtes SQL) pour un seul clic.

## Décisions

### 1. Un lot par nature de travail, plus aucun fourre-tout

La règle : le lot d'une tâche dit ce qu'elle fait, pas l'heure dont elle a hérité. Une première
version gardait les créneaux historiques (un lot `grist` pour la seule `sync-webinaires`) ; elle
a été abandonnée en revue, faute de critère lisible.

| Lot | Heure (UTC) | Nature | Contenu |
|---|---|---|---|
| `synchros` | 02:00 | recopier une source externe dans nos tables | `sync-sites`, `sync-inventory`, `sync-webinaires`, `sync-connectors`, `sync-tags`, `refresh-rpe` |
| `maintenance` | 06:00 | vérifier ou entretenir l'application | `check-s3-backups`, `cleanup-dashboards`, `facade-audit`, `slack-feedback`, `suggest-tags` |
| `tableaux` | 06:00 | rafraîchir les tableaux de bord | les tableaux de bord cronnés et leurs publications |
| `xl` | 06:00 | tâches trop lourdes pour un conteneur M | `generate-conversation-embeddings` |

Les synchros passent avant les tableaux de bord qu'elles alimentent, et à l'écart de la fenêtre de
06:00.

`DEFAULT_BATCH` disparaît. Une tâche système dont le `CRON.md` ne déclare pas de `batch:` fait
**échouer la découverte** au lieu d'atterrir quelque part en silence. Les tableaux de bord et les
publications n'ont pas de front-matter : leur lot est fixé explicitement dans le code.

Trois conteneurs tournent en parallèle à 06:00 au lieu d'un seul en série, et la partie dont la
taille n'est pas bornée — le parc de tableaux de bord — n'allonge plus le conteneur qui vérifie les
sauvegardes.

Les six synchros s'enchaînent en série dans un seul conteneur : 37 minutes de timeouts cumulés au
pire, bien avant 06:00. Une quatrième ligne reste libre dans `cron.json`.

### 2. Budget de lot, déclaré là où vit le lot

La durée maximale d'un lot se déclare dans `cron.json`, à côté de son batch. Sans elle, pas de
budget : les lots courts n'en ont pas besoin.

Le lot `tableaux` porte 3600 s : les jours complets ont pris 2150 à 3150 s, et un budget en dessous
laisserait des tableaux de bord et toutes les publications en `skipped` chaque jour (F24).

Au dépassement, constaté **entre deux tâches** : la tâche en cours va au bout, aucune nouvelle n'est
lancée, chaque tâche non exécutée reçoit une ligne `cron_runs` en statut `skipped` portant la
raison, et une **seule** alerte Slack résume ce qui n'a pas tourné.

Rien n'est tué au milieu d'une écriture. Un lot amputé cesse d'être indiscernable d'un lot réussi,
ce qui est la même exigence que F1 et F2.

### 3. Pas de priorités

L'audit propose d'ordonner les tâches par criticité. Une fois les tableaux de bord isolés, les lots
`synchros` et `maintenance` sont bornés par les fichiers du dépôt. Un champ `priority:` serait de
l'ordonnancement pour un problème que la découpe fait disparaître. À écrire le jour où la mesure le
réclame, pas avant.

### 4. Le run manuel s'exécute dans son propre conteneur

`POST /api/cron/{slug}/run` résout le slug **une fois**, demande à l'API Scalingo un conteneur
one-off qui rejoue le chemin de production (`python -m web.cron --app <slug>`), et répond
immédiatement avec l'identifiant du conteneur. Le process web ne porte plus ni le sous-processus, ni
sa mémoire, ni son temps.

L'essaimage vers les publications actives part dans le conteneur, pas dans la route : `--app <slug>`
traite le tableau de bord **puis** ses publications. Sinon un clic créerait autant de conteneurs que
de publications.

Sans jeton Scalingo configuré — développement local, review apps — la route répond 503 avec un
message qui renvoie à la ligne de commande. Un second chemin d'exécution réintroduirait
discrètement le défaut qu'on corrige ; le coût assumé est la disparition du bouton en
développement.

Deux variables de configuration nouvelles, lues par `web/config.py` comme tout le reste :
l'identifiant de l'application et le jeton d'API, ce dernier échangé contre un bearer auprès du
service d'authentification Scalingo, avec timeout explicite.

## Tests

- **Découverte** : une tâche système sans `batch:` échoue bruyamment ; tout `batch:` déclaré a sa
  ligne dans `cron.json` (le test de cohérence existant couvre déjà ce sens) ; les tableaux de bord
  et publications atterrissent dans `tableaux`.
- **Budget** : un lot dépassé enregistre les tâches restantes en `skipped` et n'alerte qu'une fois ;
  un lot sans budget déclaré se comporte comme aujourd'hui.
- **Client Scalingo** : échange de jeton, lancement du one-off, erreur réseau, timeout explicite,
  tout en `httpx` mocké — aucun appel réel.
- **Route** : répond 202, n'exécute rien dans le process web, ne découvre qu'une fois, répond 503
  sans jeton configuré.
- **Essaimage** : `--app <slug>` traite le tableau de bord puis ses publications, dans cet ordre.

## Hors périmètre

F14 (téléchargements S3 séquentiels), F15 (client boto3 sans timeout ni retry), F11, F12, F17, F18,
F20, F21 et les constats J. La parallélisation des tâches **à l'intérieur** d'un lot n'est pas
traitée : la découpe en conteneurs donne déjà du parallélisme entre lots.

## Risques

La route dépend désormais d'un service externe pour une action qui marchait en local. Un jeton
absent ou invalide retire le bouton plutôt que de dégrader silencieusement — c'est voulu, mais ça se
verra le jour où le jeton expirera.

Le changement d'heure de `sync-inventory` (03:00 vers 02:00, après `sync-sites`) est le seul effet
observable en production sur des données existantes.
