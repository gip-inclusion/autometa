# La stratégie

Document de référence technique. Le « pourquoi » en langage humain est dans [`01-pourquoi.md`](01-pourquoi.md) ; l'ordre de déploiement dans [`03-roadmap.md`](03-roadmap.md) ; la mise en place concrète dans [`04-phases.md`](04-phases.md).

## Principe directeur

Deux garanties, un seul modèle mental : **non-régression** + **anti-slop**. Cadence *fail fast, fail cheap* : attraper gratuitement et tôt ce qui peut l'être, réserver le lent / coûteux / non-déterministe à plus tard.

Le modèle d'enforcement : **« les règles dans les prompts sont des requêtes ; les vérifications déterministes sont des lois »**. La conformité d'un agent à des instructions décroît à mesure qu'on en empile — elles entrent en concurrence avec la tâche de code et perdent. D'où une **défense en profondeur** : trois couches concentriques, chacune rattrape ce que la précédente laisse passer.

## Le modèle en cercles concentriques

Plus on est au **centre**, plus c'est **rapide, déterministe, étroit**. Plus on va vers le **bord**, plus c'est **lent, non déterministe, large**.

```
  ┌──────────────────────────────────────────────────────────────┐
  │ ⑤ PROD · monitoring (Sentry, OTel)  → réalité, observe         │  non déterministe
  │ ┌──────────────────────────────────────────────────────────┐ │
  │ │ ④ NIGHTLY    → vrais services + mutation + évals          │ │  non déterministe
  │ │              → NE BLOQUE PAS (rapport)                     │ │  lent · large
  │ │ ┌──────────────────────────────────────────────────────┐ │ │
  │ │ │ ③ CI / PULL REQUEST · LE MUR                          │ │ │
  │ │ │   toute la suite hermétique + couverture du diff     │ │ │  DÉTERMINISTE
  │ │ │   + reviewer indépendant · BLOQUE LE MERGE           │ │ │  bloquant
  │ │ │ ┌──────────────────────────────────────────────────┐ │ │ │
  │ │ │ │ ② PRE-COMMIT (local) : lint + unit + anti-slop   │ │ │ │  déterministe
  │ │ │ │   BLOQUE LE COMMIT                               │ │ │ │  bloquant · local
  │ │ │ │ ┌──────────────────────────────────────────────┐ │ │ │ │
  │ │ │ │ │ ① HOOKS (pendant que l'agent code)            │ │ │ │ │  DÉTERMINISTE
  │ │ │ │ │   après écriture : lint le fichier édité      │ │ │ │ │  fail-fast (s)
  │ │ │ │ │   au moment de conclure : suite verte + test  │ │ │ │ │  in-loop
  │ │ │ │ │ ┌──────────────────────────────────────────┐ │ │ │ │ │
  │ │ │ │ │ │ ⓪⁻ CONTRATS  (types, validation, façade) │ │ │ │ │ │  rend l'erreur
  │ │ │ │ │ │ ⓪  SKILLS / RULES → l'agent ESSAIE       │ │ │ │ │ │  impossible / guide
  │ │ │ │ │ └──────────────────────────────────────────┘ │ │ │ │ │
  │ │ │ │ └──────────────────────────────────────────────┘ │ │ │ │
  │ │ │ └──────────────────────────────────────────────────┘ │ │ │
  │ │ └──────────────────────────────────────────────────────┘ │ │
  │ └──────────────────────────────────────────────────────────┘ │
  └──────────────────────────────────────────────────────────────┘
       centre : rapide · déterministe · étroit
       bord   : lent · non déterministe · large
```

**Le principe qui gouverne tout le schéma :**

> **On ne bloque jamais sur un signal non déterministe.** Les gates déterministes (anneaux ①–③) forment une coquille autour de l'agent. Ce qui est non déterministe — le guidage au centre (⓪), les évals et la prod au bord (④–⑤) — *informe* mais ne *bloque* jamais.

Le non-déterministe est donc au centre (le guidage) **et** au bord (qualité LLM, monde réel) ; entre les deux, une coquille déterministe qui bloque. On enveloppe un agent imprévisible dans des gates prévisibles.

### Rôle de chaque anneau

| Anneau | Mécanisme | Comportement | Déterministe | Bloque |
|---|---|---|---|---|
| ⓪⁻ | Contrats (types, validation, façade) | Rendent une faute *impossible à exprimer*, avant tout test | Oui | — (par construction) |
| ⓪ | Skills / rules | Proposent une démarche ; l'agent *essaie* | Non | Non |
| ① | Hooks — après écriture | Lint le fichier édité, renvoie l'erreur à l'agent | Oui | Nudge |
| ① | Hooks — au moment de conclure | Refuse de finir si suite rouge ou source sans test | Oui | **Oui, in-loop** |
| ② | Pre-commit | Lint + unit + anti-slop ; filet local | Oui | **Oui, le commit** |
| ③ | CI / PR | Suite hermétique + couverture du diff + reviewer | Oui | **Oui, le merge** |
| ④ | Nightly | Vrais services, mutation, évals → rapport | Partiel | **Non** |
| ⑤ | Monitoring prod | Ce que les tests ne peuvent structurellement pas attraper | — | Alerte |

## Les niveaux de test

Un seul axe les distingue : **ce dont le test a besoin pour tourner** (donc son coût et son déterminisme).

| Niveau | A besoin de | Marqué par | Tourne |
|---|---|---|---|
| **unit** | rien (mémoire, fakes) | *aucun marqueur (défaut)* | pre-commit + PR |
| **integration** | Postgres + Redis + `TestClient` | `@pytest.mark.integration` | PR + nightly |
| **e2e** | flux complet en process (runner + Redis + SSE, agent fake) | `@pytest.mark.e2e` | PR + nightly |
| **external** | vrai monde (Matomo/Metabase/Claude réels, credentials) | `@pytest.mark.external` | **nightly seul** |
| **évals** *(circuit à part)* | vrai LLM, jugement | hors pytest, dossier `evals/` | nightly, **non bloquant** |

**Le critère PR vs nightly n'est pas le scope, c'est l'hermétisme.** Un test e2e qui traverse HTTP → runner → Redis → SSE mais avec Redis en mémoire et l'agent faké est **hermétique et déterministe** → il tourne sur la PR, quel que soit son ampleur. Seul ce qui touche le **monde réel** (vrais services, vrais credentials, vrai LLM) part en nightly — parce que c'est non déterministe, lent, et qu'un fork pourrait exfiltrer des secrets en PR.

Le vocabulaire de marqueurs reste **minimal** (ce que font les gros repos à notre échelle) : `integration` est l'axe de travail ; `e2e`/`external` sont des marqueurs additionnels pour la sélection nightly. **Pas d'auto-marquage par chemin** ; on déclare le marqueur en tête de fichier, et `--strict-markers` rejette tout marqueur mal orthographié.

## Le scope des tests par anneau

La granularité dépend de l'anneau, parce que les anneaux ont deux métiers différents :

- **Anneaux ①–② (feedback à l'agent)** → **sous-ensemble pertinent, vite**. C'est là que « ne relancer que les tests touchés » a un sens : un outil mappe code → tests via la couverture et ne relance que les tests impactés par la modification. Boucle en secondes.
- **Anneau ③ (gate de merge)** → **toute la suite hermétique, sans sélection**. *Pas trop fin* : au gate on ne se contente jamais des tests touchés, parce qu'un changement dans le module A peut casser un test du module B — invisible à une sélection par diff. La sûreté du merge exige l'exhaustivité.
- **Anneau ④ (nightly)** → **on scope le coûteux**. La mutation tourne seulement sur les modules changés ; les évals seulement si le diff touche le code/les prompts de l'agent. *Pas trop large* : on ne paie pas le monde entier chaque nuit.

> Règle : sélection étroite dans la boucle locale pour la vitesse ; suite exhaustive au gate pour la sûreté ; scope-au-diff réservé au coûteux. La sélection par diff n'est **jamais** le gate — c'est un accélérateur de boucle, pas une garantie.

## Catalogue des mécanismes

### Garantir qu'un test existe et qu'il vérifie

- **Plancher de couverture (cliquet global)** — la couverture globale ne peut pas descendre sous une baseline mesurée. En **couverture de branches** (exerce chaque chemin), pas seulement de lignes.
- **Couverture du code modifié (le levier n°1)** — toute ligne ajoutée/modifiée dans une PR doit être exercée, à seuil élevé, indépendamment de la dette legacy. C'est « chaque modif a un test » rendu mécanique.
- **Détecteurs de slop** — un test creux passe la couverture. On l'attrape par : des règles de lint toutes faites (tests sans assertion utile, assertion dans un `except`, `pytest.raises` trop large) **et** un petit contrôle maison (test **sans assertion**, assertion **tautologique** type `assert x == x`, test qui **mocke le module qu'il prétend tester**).
- **Mutation testing** — la seule mesure de la *force* d'un test : on introduit de petits bugs dans le code et on vérifie qu'un test s'en aperçoit. Un mutant qui survit = un test creux ou un cas manquant. **Coûteux → nightly, sur le diff / modules critiques, jamais en gate.**

### Empêcher la régression in-loop

- **Hooks (anneau ①)** — après chaque écriture : lint le fichier édité, renvoyer l'erreur à l'agent (fail fast). Au moment de conclure : refuser tant que la suite n'est pas verte ou qu'un source modifié n'a pas de test. Avant écriture : bloquer les zones interdites.
- **Reviewer indépendant** — un second agent en **contexte vierge**, qui voit le diff et la spec mais pas le raisonnement de l'auteur ; il ne peut donc pas valider par réflexe les hypothèses du premier. Contre le travers central du code IA : l'agent teste *ce qu'il a imaginé*, pas la réalité.
- **Commiter les tests d'abord, en échec** — discipline gratuite : si l'agent affaiblit ensuite une assertion pour passer au vert, le `git diff` l'expose.

### Remplacer le réel sans mentir : *fake > mock*

- **Fake** = vraie petite implémentation d'une dépendance (un Redis en mémoire, une interception au niveau HTTP qui rejoue une vraie réponse). Le code testé ne sait pas qu'il parle à un faux → on teste son **comportement**.
- **Mock** = objet qui intercepte des appels et répond ce qu'on lui dit. Couple le test à la *plomberie interne* (« telle méthode appelée dans cet ordre ») → fragile, et peut faire passer un test que le code soit correct ou non.
- **Règle** : fake quand il en existe un ; mock seulement aux frontières qu'on ne possède pas (le subprocess Claude, Notion). Remplacer le mock S3 actuel (qui bricole les attributs internes du client) par une interception au niveau HTTP.

### Isolation & flaky

- **Isolation DB** — chaque test integration part d'une base propre. Vidage entre tests (notre approche), mais avec la **liste de tables dérivée automatiquement du modèle** (plus de fuite silencieuse quand on ajoute une table). Rollback en option pour le sous-ensemble en lecture seule. Vrai Postgres, jamais SQLite (parité moteur : JSONB, schémas, `TRUNCATE CASCADE`, PostGIS).
- **Parallélisation** — plusieurs tests en parallèle avec **une base par worker**, pour que le temps de CI n'explose pas à mesure que l'agent ajoute des tests.
- **Anti-flaky** — **aucun retry aveugle** (il enterre les régressions). À la place : délai max court par test + sentinelles qui *font échouer* un test qui laisse fuir une connexion/ressource. Quarantaine (isolé + ticket) plutôt que relance.

## La fondation : les contrats (anneau le plus interne)

Les contrats sont **plus internes que les tests** : ils attrapent l'erreur avant qu'un seul test ne tourne, ou la rendent carrément impossible. Principe : **rendre les états illégaux non-représentables**. Chaque contrat posé **supprime une classe entière de tests** (et de slop que l'agent ne peut plus écrire).

État actuel : le repo a le *vocabulaire* des contrats (annotations de type, un type de retour `QueryResult`) mais **aucune couche qui les fait respecter**. Comparé à TypeScript, deux couches manquent :

| En TypeScript | Ce que ça attrape | Équivalent Python | État |
|---|---|---|---|
| Le compilateur | rename, symbole manquant, mauvaise forme — *statiquement* | vérificateur de types (mypy/pyright) | **absent** |
| Zod | une donnée externe ne respecte pas le schéma — *à la frontière* | Pydantic | **absent dans web/lib** |

Les trois leviers (détaillés en phases) :
1. **Vérificateur de types**, démarré strict sur la petite façade (`lib.query`, `web.config`) puis élargi au cliquet. C'est le compilateur manquant ; un rename casse immédiatement, sans attendre l'exécution.
2. **Validation des données aux frontières externes** (réponses Matomo/Metabase, payloads `/api/query`) : on parse en schéma, on échoue fort à la frontière au lieu de propager une forme fausse.
3. **Façade à imports restreints** : une surface étroite et stable, le reste interdit — pour borner ce qu'on doit garder stable.

## Le double circuit du LLM

Le backend agent a deux comportements de nature différente, qu'on teste séparément.

- **Circuit déterministe (sur la PR, bloquant)** — tout ce qui, à entrée égale, donne la même sortie : construction du prompt, découpage du flux de réponse, aiguillage des outils, persistance, spawn/timeout du subprocess. Testé **sans vrai Claude** : on rejoue un **transcript enregistré** (une vraie sortie capturée une fois) et on vérifie la transformation ; le subprocess est faké à sa frontière. La forme du prompt et des événements est figée par snapshot (le *format*, jamais le sens).
- **Circuit qualité (en nightly, non bloquant)** — *la réponse de Claude est-elle pertinente, juste, complète ?* Non déterministe → **évals** dans un dossier `evals/` séparé : un jeu de questions représentatives, un verdict **exact** quand il y a une vérité claire (le bon outil/la bonne source a-t-il été utilisé) et un **juge LLM** quand c'est ouvert (pertinence, ton), avec grille explicite et option « je ne sais pas ». Déclenché si le diff touche le code/les prompts de l'agent.

> Frontière dure : zéro réseau/LLM dans le circuit déterministe ; le snapshot ne juge jamais la pertinence, seulement le format.

## La justesse des données

Tout le reste protège le **tuyau** ; ce produit est de l'**analytics**, et sa valeur est de produire des **chiffres justes**. Un SQL qui joint mal ou un filtre de date décalé donne du plausible-mais-faux qu'aucun gate de code ne voit. Discipline propre aux produits data :

- **jeux de données de référence** (« golden datasets ») : une petite base figée dont on connaît les bonnes réponses, contre laquelle on assert le résultat des requêtes — « elle rend 42 », pas juste « elle s'exécute » ;
- **invariants sur les données** : une somme de pourcentages fait 100, un compte n'est jamais négatif, un total détaillé égale le total agrégé, pas de doublons sur une clé ;
- **cohérence inter-sources** : le même indicateur vu par deux chemins donne le même nombre.

D'autant plus critique que c'est l'agent qui écrit le SQL — c'est exactement là qu'il produit du faux crédible.

## L'art d'écrire un test

Le métier, par opposition à la machinerie. Ces principes vivent dans l'anneau ⓪ (skill `/tdd` + `.claude/rules/tests.md`) ; les anneaux extérieurs ne font que les vérifier.

- **On teste des comportements, pas des entrées.** Une fonction a une infinité d'entrées mais un nombre fini de comportements. On regroupe les entrées qui doivent produire le même résultat (**classes d'équivalence**) et on prend **un représentant par classe**. Cinq sorties = ~cinq cas, pas cinquante.
- **Les bugs vivent aux frontières.** Si une sortie change à `score > 0.8`, on teste pile `0.8` et juste à côté. C'est le seul endroit où l'on densifie.
- **L'erreur est une sortie comme une autre.** « Cette entrée lève une erreur » est un comportement à part entière, asserté explicitement (`pytest.raises`).
- **`parametrize` aplatit.** Un même comportement avec des entrées différentes → une fonction + une table, jamais des fonctions copiées-collées. Cinq comportements = cinq lignes.
- **On ne multiplie pas les paramètres indépendants.** 3 paramètres × 4 valeurs ≠ 64 tests : on teste chaque dimension séparément, on ne combine que ce qui interagit vraiment.
- **Ce qu'on ne teste PAS** : le framework et les librairies tierces, les accesseurs triviaux, la plomberie interne privée. Critère : « si je casse cette ligne, un humain s'en plaindrait-il ? » Sinon, pas de test.
- **Tester le comportement, pas la plomberie.** Un bon test passe par la porte d'entrée publique et survit à un renommage interne. S'il casse au moindre refactor sans changement de comportement, il est mal couplé.
- **Le test doit être déterministe lui-même** : pas d'horloge réelle (on fige le temps), pas de hasard non maîtrisé, pas de `sleep` (on attend une condition), pas de dépendance à l'ordre des tests. La plupart des flaky viennent de là.
- **Forme** : un comportement par test (un échec localise tout de suite), structure Préparer → Agir → Vérifier, et un **nom qui décrit le comportement**. Les tests sont la documentation vivante.
- **Un bug = un test d'abord.** À la découverte d'un bug : écrire le test qui le reproduit (rouge), *puis* corriger (vert). Le test reste pour toujours → ce bug ne peut plus jamais revenir en silence.
- **La couverture est une boussole, pas une cible.** Dès qu'un chiffre devient un objectif, on le gonfle de tests creux (loi de Goodhart). D'où l'empilement couverture de branches + mutation + revue.

## Définition de « fait »

Un changement est suffisamment testé quand sont couverts : (a) le **chemin nominal**, (b) au moins un **cas d'erreur/limite** pertinent, (c) les **invariants des zones critiques** touchées. La couverture de ligne est nécessaire mais **pas suffisante** : un test qui s'exécute sans asserter est un **critère de rejet** (`.claude/rules/review.md`). C'est le rôle du mutation testing et du détecteur de slop de rendre « les tests passent » insuffisant pour tromper le gate.

## Quoi tourne, quand

```
                     UNIT  INTEGRATION  E2E  EXTERNAL  ÉVALS  MUTATION  MONITORING
 pre-commit (local)   ✅    (lint+gate)   –      –       –        –          –
 Pull Request (CI)    ✅       ✅         ✅     –        –        –          –
 Nightly (cron)       ✅       ✅         ✅     ✅       ✅       ✅          –
 Prod (continu)       –        –          –      –        –        –          ✅
```

Budget cible : pre-commit ~secondes, suite PR ~quelques minutes, nightly libre.
