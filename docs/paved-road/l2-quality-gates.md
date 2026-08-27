# L2 — Quality Gates

Ce niveau protège **tout le monde** — paved road ou pas, Claude ou Codex, humain ou cron. Il ne dit
pas comment bien travailler ; il dit ce qui sera vrai quoi qu'il arrive.

Origine et justifications : `docs/plans/2026-07-28-autometa-paved-road-design.md`, section « L2 —
Quality Gates ».

## Ce que L2 garantit, et ce qu'il ne garantit pas

La garantie tient en une phrase : **aucun rouge ne peut atteindre `main`**. Elle vient de la
protection de branche GitHub, hors de portée de l'agent puisqu'elle ne tourne pas dans l'agent.

Elle ne garantit pas que le travail soit *le bon* travail — c'est l'objet de L0 — ni qu'une preuve
soit sincère au-delà de son code de sortie. Le `pre-push` ne garantit rien du tout : `--no-verify`
le contourne, c'est un service de confort qui évite un aller-retour de CI.

## Les checks requis

Cinq portent sur le code, en anglais, et s'adressent à qui sait les lire. Le sixième s'appelle
**« Ce qui devait marcher »** et n'a qu'un lecteur : la personne non technique qui regarde la boîte
de merge. Son résumé affiche le tableau des `DOD-N` avec démontré / non démontré, et la famille de
l'échec en français. C'est le seul qu'elle consulte ; les cinq autres peuvent rester techniques.

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

**État au 2026-08-18** : les cinq checks techniques sont requis. « Ce qui devait marcher » ne l'est pas
encore — il n'existera sur GitHub qu'après le merge de ce lot, et devra être ajouté à ce moment-là.

`strict: true` est armé. Sans ce drapeau, GitHub accepte de merger une PR dont la CI a été verte sur
une base périmée : deux branches ajoutent chacune une migration enfant du même `down_revision`, les
deux sont vertes, et `main` se retrouve avec deux heads Alembic.

## Le déclencheur de périmètre

> Le check paved road est requis **si et seulement si** le diff touche `web/`, `lib/`, `skills/` ou
> `alembic/`. Sur ce périmètre, l'absence de `definition-of-done.md` est un échec, pas une
> non-application. Ailleurs — dépendances, `docs/`, `knowledge/` — il est neutre.

Sans déclencheur écrit, deux issues, toutes deux mauvaises : un check exigé sur toutes les PR gèle le
dépôt, puisque Dependabot en ouvre jusqu'à vingt par jour ; un check jamais exigé se contourne en
n'écrivant pas de Definition of Done.

La seule échappatoire est un label `break-glass`, posé à la main par un humain. Le check le journalise
comme tel dans son résumé, avec la liste des fichiers couverts par la dispense : une dispense implicite
n'en est pas une, c'est une porte que personne ne regarde.

## La CI rejoue, elle ne fait pas confiance

Pour chaque `DOD-N`, la CI relance la commande enregistrée dans l'attestation et compare son propre
code de sortie au verdict journalisé. **Tout écart est un échec.** Le journal redevient ce qu'il est —
un cache et une source de statistiques — et cesse d'être une autorité.

Le rejeu exécute donc une commande lue dans un fichier de la PR. Ce n'est pas une surface nouvelle :
le job `Tests` exécute déjà le code de la PR, le workflow se déclenche sur `pull_request` et non
`pull_request_target`, ses permissions sont limitées à `contents: read`, et GitHub n'expose pas les
secrets du dépôt aux PR issues d'un fork.

Une attestation est aussi refusée quand le contenu qu'elle prouve a changé depuis : la comparaison
porte sur les empreintes d'arbre des chemins prouvés, ce qui rend le rebase inerte et une vraie
modification du code invalidante.

## Les familles d'échec

Un compteur d'échecs est un mauvais outil, parce que les échecs n'appellent pas la même réponse.
Chaque échec restitué porte donc sa famille.

| Famille | Ce que c'est | Réponse |
|---|---|---|
| **A** | test rouge, preuve périmée, rejeu divergent | l'agent reprend — c'est le travail normal |
| **B** | Postgres, Redis ou le réseau injoignable | arrêt immédiat : réessayer brûle du temps sans rien corriger |
| **C** | Definition of Done absente ou mal formée | retour au citizen developer |
| **D** | contenu interdit sous `attestations/` — le dépôt est public | break-glass |

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
