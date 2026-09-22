# L2 — Quality Gates

Ce niveau protège **tout le monde** — paved road ou pas, Claude ou Codex, humain ou cron. Il ne dit
pas comment bien travailler ; il dit ce qui sera vrai quoi qu'il arrive.

Origine et justifications : `docs/plans/2026-08-22-paved-road-workflow.md`, section « L2 —
Quality Gates ».

## Ce que L2 garantit, et ce qu'il ne garantit pas

La garantie tient en une phrase : **aucun rouge ne peut atteindre `main`**. Elle vient de la
protection de branche GitHub, hors de portée de l'agent puisqu'elle ne tourne pas dans l'agent.

Elle ne garantit pas que le travail soit *le bon* travail — c'est l'objet de L0 — ni qu'une preuve
soit sincère au-delà de son code de sortie. Le `pre-push` ne garantit rien du tout : `--no-verify`
le contourne, c'est un service de confort qui évite un aller-retour de CI.

## Les checks requis

Ils portent sur le code, en anglais, et s'adressent à qui sait les lire. Il n'y en a plus aucun qui
s'adresse à la personne non technique : le job « Ce qui devait marcher » a été supprimé le
2026-08-30, pour la raison exposée plus bas. Ce qu'elle lit désormais, c'est la description de PR,
que `pr.md` compose à partir du contrat et des attestations.

`CodeQL` et `GitGuardian` tournent sur le dépôt et **ne sont pas requis** : ils appartiennent à des
tiers, leur disponibilité ne nous appartient pas, et un check requis indisponible bloque tout.

Les noms requis sont les chaînes littérales publiées par GitHub, pas les identifiants de job. Un
contexte inconnu reste indéfiniment « Expected — Waiting for status to be reported », et
`enforce_admins` interdit de forcer le passage : toutes les PR seraient bloquées sans message.
`scripts/check_required_checks.py` compare la liste requise aux `name:` de `ci.yml` et échoue en cas
de dérive — sans lui, renommer un job éteindrait la protection en silence.

Le contrôle de dérive est **asymétrique**, et c'est délibéré : un check requis absent de `ci.yml`
gèle le dépôt, donc il bloque ; un job déclaré dans `ci.yml` et pas encore requis est une lacune de
couverture, donc il avertit. La raison est structurelle — un check neuf ne peut pas être inscrit avant
d'avoir été publié une première fois, sinon il reste en « Expected » sur toutes les PR. Un renommage
reste attrapé : il produit les deux écarts à la fois, dont le bloquant.

**État au 2026-08-30** : les checks techniques sont requis. « Lint front (Biome) » ne l'est pas
encore — un check neuf n'existe sur GitHub qu'après avoir été publié une première fois, et devra
être ajouté à ce moment-là.

`strict: true` est armé. Sans ce drapeau, GitHub accepte de merger une PR dont la CI a été verte sur
une base périmée : deux branches ajoutent chacune une migration enfant du même `down_revision`, les
deux sont vertes, et `main` se retrouve avec deux heads Alembic.

## La CI ne lit aucun artefact du parcours

Ce document a longtemps décrit un job « Ce qui devait marcher » qui rejouait les commandes des
attestations et comparait son code de sortie au verdict journalisé. **Ce job n'existe plus depuis
le 2026-08-30, et c'est un choix, pas un oubli.**

La CI porte des tests, de la sécurité, des audits, des builds d'image et des déploiements. Elle ne
relit pas des documents produits par le workflow de développement : ce qu'elle y mesurerait, c'est
ce que ce workflow a bien voulu écrire. La supprimer vaut mieux que l'aménager.

Ce qui reste, et qui tient la preuve :

- une attestation est refusée dès que le contenu qu'elle prouve a changé — la comparaison porte sur
  les empreintes d'arbre des chemins prouvés, ce qui rend le rebase inerte et une vraie
  modification du code invalidante ;
- `advance` est la seule voie pour passer d'un état au suivant, et il n'avance que sur des codes de
  sortie réels ;
- la liste d'interdits de `.claude/settings.json` refuse à l'agent l'écriture des attestations et
  du journal par ses outils d'édition. Ce que cela ne ferme pas, et il faut le dire : rien
  n'empêche un `sed -i`, un `tee` ou un script d'y écrire — il n'y a pas de bac à sable, la couche
  2 du design n'est pas construite ;
- le pair lit le contrat, le journal et les attestations dans la PR.

Ce qu'on perd, et qui est assumé : rien du côté GitHub ne constate qu'une PR touchant `web/` a un
contrat démontré. La garantie est locale, et le déclencheur de périmètre — `web/`, `lib/`,
`skills/`, `alembic/` — reste une règle de revue, plus un check.

## Les familles d'échec

Un compteur d'échecs est un mauvais outil, parce que les échecs n'appellent pas la même réponse.
Chaque échec restitué porte donc sa famille.

| Famille | Ce que c'est | Réponse |
|---|---|---|
| **A** | test rouge, preuve périmée, rouge manquant avant un vert, **et aussi la definition of done absente ou mal formée** | l'agent reprend — c'est le travail normal |
| **B** | Postgres, Redis ou le réseau injoignable | arrêt immédiat : réessayer brûle du temps sans rien corriger |
| **C** | critère ambigu ou infaisable | retour au citizen developer |
| **D** | contenu interdit sous `paved-road/` — le dépôt est public | arrêt : la décision remonte à un humain |

Écart à connaître entre ce tableau et le code : la famille est déclarée **par check**, pas par
cause (`lib/attestation.py`, `CHECKS`). Seul `doctor` porte B, seul `content` porte D, et **aucun
check n'émet C** — une definition of done absente est restituée en A. Une panne réseau pendant
`make security` sera donc annoncée « réparable », à tort.

## Les trois angles morts traités au même moment

Rendre la CI obligatoire n'a d'intérêt que si elle regarde ce qu'on croit qu'elle regarde.

**`skills/` échappait à trois gates déjà payés** — lint restreint, bandit exclu, couverture aveugle —
alors qu'il s'y trouve une trentaine de fichiers Python, dont certains écrivent en base et sur S3.
Mesure préalable avant inclusion : zéro violation de lint, zéro issue bandit de sévérité moyenne ou
haute, et 1262 instructions jamais exécutées qui entrent dans le calcul de couverture. Le plancher
global a donc baissé — parce que le périmètre a grandi, pas parce que l'exigence a baissé.

**Le job `Migrations` tourne sur une base vide**, donc toute migration dépendante des données y est
verte par construction. L'incident est dans l'historique : `b12cbac64ff9` a dû se voir ajouter sept
remplissages avant ses `alter_column`, « sinon la migration échoue en prod ». La seconde passe contre
un dump anonymisé de staging reste à établir ; en attendant, un signal refuse toute contrainte non
nulle posée sans remplissage préalable dans le même `upgrade()`.

**La CI réécrivait chaque commande au lieu d'appeler le `Makefile`**, et la dérive était déjà là : un
CVE ignoré d'un côté et pas de l'autre, des périmètres de lint différents. Les jobs appellent
désormais les cibles, les chemins et exclusions étant définis une seule fois.

## Auto-protection par CODEOWNERS

Les fichiers de gate exigent une approbation humaine — **dès que `require_code_owner_reviews` est
armé** : au 2026-08-18 il ne l'est pas, `CODEOWNERS` n'étant pas encore sur `main`, où GitHub le lit.
Le critère d'inscription n'est pas l'importance
du fichier mais la fréquence à laquelle du travail ordinaire le touche : un `CODEOWNERS` qui se
réveille tous les jours produit des approbations en série sans lecture, ce qui vaut moins que pas de
`CODEOWNERS` du tout. `web/models.py` et `alembic/` en sont volontairement exclus.

Ses deux modes de panne sont muets, et c'est ce qui les rend dangereux : une entrée dont le titulaire
n'a pas un droit `write` explicite est ignorée sans erreur, et un ensemble d'owners réduit à une
personne rend impossible toute PR de cette personne sur un fichier de gate. Le job `Security`
interroge donc `/codeowners/errors` à chaque exécution — c'est le seul moyen d'apprendre qu'un
guardrail s'est éteint.
