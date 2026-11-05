# Agents, version 2 : sous-agents, préparations, cadence

Révision de #278 demandée par Alexis le 04/11, après test en review app, étendue le 05/11
(sous-agents génériques, plantage -9). Le brief cite
`paved-road/agents-confirmation/` ; le contrat de #278 vit dans `paved-road/agents-creation/`,
gardé tel quel pour ne pas déplacer un contrat déjà relu.

## Le plantage « code -9 »

Le message « Process exited with code -9: » sans stderr veut dire que le processus du CLI
Claude a été tué de l'extérieur. Autometa ne tue le CLI que sur annulation, budget d'appels ou
arrêt, et ces trois chemins laissent une autre trace. La cause la plus probable est la limite
mémoire du conteneur de la review app. Les logs Scalingo ne sont pas accessibles d'ici (le jeton
n'existe que dans les secrets de CI) : ce qui suit vient du dépôt, de la documentation Scalingo et
de mesures locales.

**Taille.** Une review app clone la formation de son application parente (`autometa-staging`) ;
`scalingo.json` l'emporte, mais seulement à la création. La taille de staging n'est écrite nulle
part dans le dépôt. `web/config.py` budgète `MAX_CONCURRENT_AGENTS` pour un conteneur de 2 Go
(XL, la prod).

**Mesures locales** (05/11, CLI natif 2.1.318 comme celui de `bin/post_compile`, HOME vide,
API Anthropic remplacée par un faux serveur local qui fait appeler `agents.py destinations`
puis répond) :

| Processus | RSS pic |
|---|---|
| worker web (`import web.app`, avant toute requête) | 150 Mio (~200 en service, `web/config.py`) |
| CLI de l'agent, tour « guide-moi pour créer un agent » | 201 à 229 Mio (~350 sur une longue conversation, `web/config.py`) |
| `agents.py destinations` lancé par l'agent | 122 Mio, 2,8 s (import de `boto3` par `web.s3`) |
| `claude --print` d'un titre ou des tags | 184 Mio chacun |
| arbre CLI du premier tour, titre et tags en parallèle | 543 Mio RSS, 377 Mio PSS |
| même arbre, titre puis tags l'un après l'autre | 402 Mio RSS, 288 Mio PSS |

Au premier message d'une conversation, avec `LLM_BACKEND=cli`, trois CLI tournent ensemble
(l'agent, le titre, les tags). Avec le worker web, le pic dépasse un conteneur M (512 Mo) ; une
longue conversation avec un appel d'outil approche L (1 Go). Le faux serveur répond tout de
suite : en vrai, les CLI se chevauchent plus longtemps, les chiffres sont un plancher.

**Ce que cette PR change.**
- Les review apps sont fixées à XL : `formation` de `scalingo.json` à la création, et
  `scripts/review_app.py` remet la taille à XL à chaque `ensure` (une review app déjà créée,
  comme celle de #278, garde sinon sa taille d'origine). XL est la taille de la prod, celle
  pour laquelle le budget d'agents est écrit, et la seule au-dessus de L.
- Les CLI courts (titre, tags) passent un par un : le pic du premier tour perd ~180 Mio.
- Un CLI tué par un signal qui ne vient pas d'une annulation donne « L'agent a été tué par le
  système (signal 9, SIGKILL), probablement faute de mémoire dans le conteneur » au lieu d'un
  message vide, et le journal consigne la mémoire du conteneur (cgroup v2, sinon v1 : limite,
  utilisée, pic, nombre d'OOM kills).
- La commande `destinations` du skill répond tout de suite, sans que l'agent cherche dans le dépôt.

Non corrigé, noté : `agents.py` importe `web.s3` (boto3, 1,3 s d'import mesurée) même pour lister les
destinations ; l'alléger demanderait de découper `lib/agents.py`, hors de cette PR.

## Version 4 : des briques génériques

Révision du 05/11, après le test complet d'Alexis en review app. Son cas (des tickets pour le
backlog commun à partir d'une base et d'une page Notion et du code GitHub, étiquetés par `clef`,
rangés dans un fichier, deux fois par semaine) a été refusé par l'agent de la v2 : ni page
Notion, ni GitHub, ni cadence bihebdomadaire, ni fichier, et un classificateur qui filtre sans
étiqueter. Correction d'Alexis : ce cas n'est qu'un exemple, rien ne doit lui être propre.

- **Préparations = connecteurs.** Un type de préparation est un fichier
  `lib/agent_connectors/<type>.py` (ce qu'il lit, ses champs, ses refus, son rendu Markdown) ;
  la liste fermée des types est `config/agent_preparations.yaml`, et rien hors de cette liste
  n'est importé. Toute source (identifiant Notion, dépôt, organisation, URL) vient de la
  configuration de l'agent. Chaque préparation accepte un `plafond` (1 000 à 200 000 caractères)
  appliqué par le registre. Types : `notion` (base filtrée, colonnes choisies, et au-delà du
  plafond un décompte déterministe par colonne suivi des lignes les plus récentes ; ou page et
  sous-pages jusqu'à une profondeur), `github` (dépôts publics d'une liste puis d'une
  organisation : README, configuration, TODO et FIXME avec chemin et ligne lus dans l'archive,
  issues et PR ouvertes, derniers commits ; au-delà du plafond total, le run suivant reprend où
  celui-ci s'est arrêté), `url` (https public, jamais une adresse privée), `s3`, `cron`.
- **Classificateur en étiquettes.** À côté du filtre (une question, sous le seuil la production
  est écartée), un mode étiquettes : de 1 à 10 étiquettes déclarées avec leur question, posées à
  `clef` en un seul appel (il en accepte 64), chaque production reçoit celles qui passent le seuil
  et n'est jamais écartée. La limite de 3 était celle des sous-agents ; elle passe à 5, et ne borne
  plus le nombre de questions. Le contrat de sortie demande un envoi par élément, pour que le
  seuil s'applique à un ticket et non à une liste.
- **Fichiers de l'agent.** Des noms déclarés dans la configuration, gardés dans S3 par Autometa,
  jamais envoyés ailleurs. Chaque fichier est donné au run ; l'agent en rend une version entière
  ou y range des productions une par une (`fichier:<nom>`, après les sous-agents). Chaque
  écriture est une version ; lire, historique et comparaison sont libres, revenir à une version
  passe par la confirmation vérifiée par le code et s'écrit comme une version de plus.
- **Cadence par jours de la semaine** (`jours: [lundi, jeudi]`), les anciennes valeurs restent.
  Pas d'heure : `run-agents` passe une fois par jour, une heure demanderait un lot de plus.

## Ce qui reste séparé

- **Le cerveau du worker** (le modèle du conteneur jetable) : hors de cette PR. Il est fixé par
  l'orchestrateur externe `autometa-jobs`, qui ne prend aujourd'hui ni modèle ni clé par pipeline.
- **Les crons et le worker** : le worker ne lance jamais de cron et ne détient aucune clé.

## Sous-agents (option a, après le run)

Liste fermée `config/agent_modeles.yaml` : trois types, chacun avec ses modèles Ollama Cloud
permis (noms relevés dans `https://ollama.com/api/tags`).

| Type | Ce qu'il fait | API | Modèles |
|---|---|---|---|
| `classificateur` | question oui/non, probabilité du oui, seuil | `/v1/systemone` | `clef:27b` |
| `extraction` | champs d'un schéma déclaré (1 à 10, texte, nombre, entier, booleen), ajoutés à la production | `/api/chat`, sortie contrainte par `format` | `glm-5.2`, `gemma4:31b` |
| `resume` | réécrit la production en 100 à 3000 caractères | `/api/chat` | `glm-5.2`, `gemma4:31b` |

Une configuration d'agent déclare jusqu'à trois sous-agents dans `outils_modeles`. Quand un run
est livré, Autometa les applique à chaque production, dans l'ordre, avant la livraison, avec sa
propre clé `OLLAMA_API_KEY` : le worker n'en détient aucune. Un classificateur sous le seuil
arrête la chaîne : production non livrée, gardée avec sa probabilité (statut `ecarte`). Une
erreur d'un maillon (réseau, clé absente, sortie hors schéma, résumé trop long) : rien de cette
production n'est livré (statut `echec_sous_agent`, avec le maillon et la raison), le run reste à
livrer et repasse au passage suivant de `run-agents`, qui sort en échec pour l'alerte. Les
journaux nomment l'envoi et le maillon, jamais le contenu. La trace du run
(`<slug>/runs/<run>.json`) compte les appels aux sous-agents.

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
`cadence` tombe, enchaîne préparations, run, et au passage suivant sous-agents et livraison.
Il hérite de `cron_runs`, de Sentry et des alertes Slack des crons.

## Grille d'actions

| Action | Garde |
|---|---|
| lire (configuration, runs, envois) | aucune |
| lancer un run maintenant | confirmation vérifiée par le code, dans un message ultérieur, utilisable une fois |
| modifier la configuration (mission, destinations, préparations, cadence, sous-agents, consigne) | plan / apply / revert, même confirmation |
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
- `url` vérifie que l'hôte résout vers une adresse publique puis lit sans suivre de redirection ;
  un DNS qui change entre la vérification et la lecture n'est pas couvert.
- GitHub sans jeton : 60 requêtes par heure, quatre par dépôt ; `GITHUB_TOKEN` d'Autometa lève la
  limite.
- Un run lancé le matin est livré au passage suivant de `run-agents`, ou à la demande (`livrer`).
- Comment le worker lit `input_uri` dépend d'`autometa-jobs`, non vérifié.
