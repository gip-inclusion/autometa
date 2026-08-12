# Autometa Paved Road — design

Un *paved road* pour citizen developers : un chemin guidé qui rend le bon choix facile, doublé de
guardrails qui s'appliquent quel que soit le chemin emprunté.

Statut : design révisé après revue contradictoire, plan de mise en œuvre à exécuter.
Date : 2026-07-28, révisé le 2026-08-11. Revue : `docs/plans/2026-08-11-paved-road-review.md`.

## Le problème

Des citizen developers doivent pouvoir demander une fonctionnalité applicative complète (route, modèle,
template, skill) et la voir arriver en production, sans savoir lire le code produit.

Quatre défaillances se produisent aujourd'hui, et elles se cumulent :

- **Le résultat n'est pas jugeable.** La CI vérifie que le code est propre et que les tests passent.
  Elle ne vérifie jamais que l'application démarre, ni qu'elle fait ce qui était demandé.
- **L'agent est juge et partie.** C'est lui qui déclare « terminé ».
- **Les règles ne sont pas exécutables.** `.claude/rules/zones-critiques.md` demande à l'agent de
  *signaler* qu'il touche une zone sensible, et annonce une « relecture humaine » que personne n'assurera.
  Une règle auto-déclarative n'est pas un guardrail.
- **Le déploiement n'est pas vérifié.** `.github/workflows/_deploy.yml` pousse vers Scalingo et s'arrête.
  Aucun contrôle de santé, aucun smoke test, aucun rollback.

Objectif : **zéro intervention d'un humain technique sur le chemin nominal.** Un chiffre global
d'« autonomie » n'aurait ni dénominateur ni mécanisme : le parcours sollicite structurellement deux
personnes non techniques par fonctionnalité — celle qui valide la Definition of Done, celle qui approuve
la PR — et la règle « en cas de doute, on classe BUSINESS » maximise les remontées par construction.

Ce qui se mesure, et qui est la vraie promesse : **la part des fonctionnalités menées jusqu'à la PR sans
qu'un contributeur technique ait eu à écrire une ligne.** Le break-glass technique est l'exception, et
son taux est un indicateur, pas un slogan.

## Décisions actées

| Sujet | Décision |
|---|---|
| Public | Citizen developers, fonctionnalités applicatives complètes |
| Autonomie | Zéro intervention d'un humain technique sur le chemin nominal ; break-glass réservé au cas grave |
| Autorité | Attestations, fitness functions, adversarial review, tests-contrat — les quatre |
| Prod | Le paved road s'arrête à la PR ; un pair citizen developer merge ; Naël promeut par tag |
| Durée | Sans contrainte, le travail se fait en AFK |
| Filiation | Déclinaison allégée de `akria-pipeline`, doctrine reprise, volume écarté |
| Trajectoire | Empilement de niveaux, jamais un déploiement en bloc |
| Outillage | Cibles du `Makefile` existant, aucune CLI propriétaire du paved road |
| Périmètre | Le rituel s'applique dès que le diff touche `web/`, `lib/`, `skills/` ou `alembic/` ; neutre ailleurs. Les tableaux de bord sont hors périmètre |
| spec-kit | Retiré ; la Definition of Done le remplace, la constitution est récupérée puis redistribuée |

### Ce qui déclenche le paved road

Sans déclencheur écrit, deux issues, toutes deux mauvaises : un check exigé sur toutes les PR gèle
le dépôt — `dependabot.yml` ouvre jusqu'à vingt PR par jour et dix auteurs ont produit 110 commits
en 90 jours, quasi tous hors paved road, y compris des correctifs de sécurité ; un check jamais
exigé se contourne en n'écrivant pas `definition-of-done.md`, ce qui rend L0 et L1 facultatifs pour
qui est pressé.

> **Le check paved road est requis si et seulement si le diff touche `web/`, `lib/`, `skills/` ou
> `alembic/`.** Sur ce périmètre, l'absence de `definition-of-done.md` est un échec, pas une
> non-application. Ailleurs — mises à jour de dépendances, `docs/`, `knowledge/` — il est neutre.

La seule échappatoire est un label `break-glass` posé à la main par un humain, et journalisé comme
tel. Une dispense implicite n'en est pas une : c'est une porte que personne ne regarde.

**Les tableaux de bord ne sont pas dans ce périmètre.** Autometa est un produit qui permet à ses
utilisateurs de créer des tableaux de bord par le chat et de les pousser en production ; ce parcours
est celui de l'*usage* du produit, pas de son *développement*. Il ne produit ni branche, ni PR, ni
diff — le code est écrit directement dans l'instance de production (`.claude/hooks/guard_write_paths.py`
l'autorise explicitement pour `data/interactive/`, et rien n'y est versionné : `git ls-files data/` ne
renvoie aucun fichier, les artefacts vivant sur S3). Le paved road ne le couvre pas et n'a pas vocation
à le couvrir. Il en découle une seule obligation dans l'autre sens, traitée en L6 : le développement de
l'application ne doit pas casser ces tableaux de bord.

## Le cœur : la Definition of Done

L'élément irréductible n'est ni la CI, ni les hooks, ni la review. C'est **un accord écrit en français
avant de coder, dont la partie décisive n'est pas « ce qu'on va faire » mais « comment on saura que
c'est fait »**.

```
   AVANT                                      APRÈS
   ┌─────────────────────┐              ┌──────────────────┐
   │ definition-of-done  │ ─ on code ─▶ │  attestations/   │
   │                     │              │                  │
   │ • criterion 1       │◀─ compare ─  │  evidence 1  ✓   │
   │ • criterion 2       │              │  evidence 2  ✓   │
   │ • criterion 3       │              │  evidence 3  ✗   │
   └─────────────────────┘              └──────────────────┘
        validé par                          regardé par
   le citizen developer                le citizen developer
```

Raison d'être : le problème n'est pas que le code soit mauvais — la CI couvre déjà bien ce risque.
Le problème est que personne ne peut juger si c'est *le bon travail*. Sans Definition of Done, un dépôt
techniquement irréprochable fabrique la mauvaise chose, proprement.

Les acceptance criteria sont **observables** : formulés de sorte qu'une personne non technique puisse
constater leur satisfaction en regardant l'application, sans interpréter. Ils constituent le référentiel
unique de tout l'aval — les tests E2E les démontrent un par un, l'adversarial review les prend pour
référence, la description de PR les récapitule.

Le fichier est rédigé **en français**. C'est le seul artefact que lit le citizen developer, et le produit
est francophone. Seul l'outillage est en anglais.

## Architecture : Guardrails, Core, Adapters

L'exigence d'agnosticité (Claude Code aujourd'hui, potentiellement Codex demain) impose une règle dure :

> **Aucun guardrail ne dépend de la marque de l'agent.** Ce qui garantit est un exécutable en ligne de
> commande, relançable par la CI et lisible par un humain. L'agent ne fait qu'appeler.

```
┌─ ADAPTERS ──────────────────────── jetable, propre à l'agent ─┐
│  hooks Claude Code · skills · Workflow tool                   │
│  → feedback précoce, confort. Ne garantit RIEN.               │
│  ┌─ CORE ───────────────────────── portable, CLI + fichiers ─┐│
│  │  state journal · advance · checks · artefacts             ││
│  │  → invocable par Claude, Codex, un humain, ou la CI       ││
│  └───────────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────────┘
┌─ GUARDRAILS ─────────────── hard stops, hors de portée de l'agent ─┐
│  branch protection GitHub · jobs CI                                │
│  → c'est ICI que rien ne peut passer.                              │
└────────────────────────────────────────────────────────────────────┘
```

Deux éléments seulement, et c'est délibéré. Les **git hooks n'y sont pas** : `--no-verify` les contourne,
et `.git/hooks/` est éditable par un agent qui dispose de Bash — c'est exactement l'argument opposé plus
bas à la falsification par `touch`. Ils rendent un vrai service de feedback précoce, ils appartiennent au
Core. Le **déploiement vérifié** n'y est pas non plus : il est hors périmètre (voir l'annexe), et le
figurer comme guardrail reviendrait à compter une garantie qui n'est pas construite.

La distinction paved road / guardrails est celle du platform engineering : le paved road dit *voilà
comment faire*, le guardrail dit *ceci sera vrai quoi qu'il arrive*. Les deux sont nécessaires et
indépendants.

Écart assumé avec `akria-pipeline` : chez Akria l'enforcement vit dans les hooks Claude Code, et le
`SKILL.md` reconnaît que sans son ancre de worktree les gates deviennent **inertes** — zéro enforcement,
silencieusement. Un guardrail qui peut s'éteindre sans bruit n'en est pas un pour un citizen developer.
Ici la garantie descend dans les Guardrails, que nul agent ne peut désarmer puisqu'ils ne tournent pas
dans l'agent. Le paved road devient ce qui *aide à passer* les gates, non ce qui les constitue.

Corollaire : **chaque check est exécutable seul, en une commande.** L'orchestrateur ne fait que les
lancer et enregistrer leurs codes de sortie.

## Les sept niveaux

Modèle de maturité numéroté, dans l'esprit des SLSA Build Levels. Chaque niveau s'ajoute sans modifier
les précédents ; le système reste cohérent à n'importe quel étage.

```
                                            friction    ce qu'on gagne
  ┌───────────────────────────────────────┐
  │ L6  FITNESS FUNCTIONS                 │   ●●●●●   la qualité ne peut
  │     blast radius ciblé, règles        │           plus se dégrader
  │     de prose devenues checks          │
  ├───────────────────────────────────────┤
  │ L5  ADVERSARIAL REVIEW                │   ●●●●○   la dette ne
  │     lentilles indépendantes           │           s'accumule plus
  │     sur le diff, verdict en français  │
  ├───────────────────────────────────────┤
  │ L4  SMOKE                             │   ●●●○○   on voit ce qu'aucun
  │     MCP, exploratoire, local          │           test n'avait prévu
  │     puis review app                   │
  ├───────────────────────────────────────┤
  │ L3  E2E                               │   ●●●○○   ça marche vraiment,
  │     Playwright, 1 test par DOD-N,     │           et ça le restera
  │     déterministe, CI + nightly        │
  ├───────────────────────────────────────┤
  │ L2  QUALITY GATES                     │   ●●○○○   rien de rouge
  │     pre-push + CI, hors agent         │           n'atteint main
  ├───────────────────────────────────────┤
  │ L1  ATTESTATION                       │   ●○○○○   plus aucun PASS sans
  │     state journal, advance, evidence  │           code de sortie 0
  │     rattachée au contenu prouvé       │
  ├───────────────────────────────────────┤
  │ L0  DEFINITION OF DONE     ← LE CŒUR  │   ○○○○○   le travail devient
  │     definition-of-done.md +           │           jugeable
  │     attestations/                     │
  └───────────────────────────────────────┘
```

### L0 — Definition of Done

Deux artefacts par fonctionnalité : `definition-of-done.md` (intention et acceptance criteria observables)
et un dossier `attestations/`.

Le moment de validation est **le seul** où l'on sollicite le citizen developer pendant la conception.
La machine lui restitue en français simple ce qu'elle a compris et ce qui sera vrai à la fin ; il valide
ou corrige. Tout le reste se déroule sans lui.

**Le paved road remplace spec-kit.** Les neuf commandes `/speckit.*`, les templates et `specs/` sont
retirés : deux parcours de spécification concurrents produiraient deux sources de vérité. La constitution
(`.specify/memory/constitution.md`) contient en revanche des invariants qui gardent leur valeur — sécurité
par conception, OWASP, RGPD, lean, transparence. Ils sont récupérés avant suppression et redistribués selon
la règle de partage ci-dessous : ceux qui sont permanents deviennent des guardrails, aucun ne survit comme
document déclaratif.

#### Format d'un acceptance criterion

Template minimal, en français, avec identifiant stable.

```
# Export PDF des rapports

## Ce que je veux
Pouvoir télécharger un rapport en PDF depuis sa page.

## Ce qui devra marcher

DOD-1 — Quand je clique sur « Exporter en PDF » depuis un rapport,
  alors un fichier PDF se télécharge.

DOD-2 — Le PDF contient le titre du rapport et ses graphiques.

DOD-3 — Sur un rapport de 10 000 lignes, le téléchargement aboutit
  en moins de 30 secondes.

DOD-4 — Quand le rapport est vide, alors un message l'indique et
  aucun fichier n'est téléchargé.
```

Le contexte n'apparaît que lorsqu'il compte (DOD-3). Gherkin complet a été écarté : quatre critères y
occupent une page, et la cérémonie fatigue un lecteur non technique qui doit précisément *lire* ce fichier.
La forme reste assez régulière pour qu'un check puisse refuser le flou et pour que le parcours de smoke (L4)
s'en dérive.

#### Tous les critères ne se démontrent pas de la même façon

L'exemple ci-dessus le montre lui-même : `DOD-1` se joue dans un navigateur, `DOD-2` porte sur le contenu
d'un fichier produit — Playwright pilote un navigateur, il ne lit pas l'intérieur d'un PDF — et `DOD-3`
est une mesure de volumétrie, source d'instabilité sur un runner partagé. Or L3 pose « un test par
`DOD-N` » et L0 pose qu'un critère infaisable est un blocage métier. Sans nuance, le parcours réel
devient : le citizen developer valide, part, et revient à « `DOD-3` n'est pas démontrable de façon
déterministe, acceptez-vous de le retirer ? » — une question technique déguisée en question métier,
précisément ce que le design interdit.

Deux règles en découlent.

**« Observable » ne veut pas dire « Playwright ».** Un critère de contenu de fichier se démontre par une
assertion sur l'artefact produit, un critère de volumétrie par une mesure en nightly hors du chemin
bloquant. La matrice de preuve admet ces formes ; L3 fournit la plus courante, pas la seule.

**Au plus cinq critères démontrés par E2E.** Au-delà, la preuve retombe sur une forme déterministe moins
coûteuse ou sur le smoke. Sans borne, le coût récurrent de L3 est une fonction non contrôlée de la
verbosité de la demande — le signal « au-delà d'une quinzaine, découpez » ne s'applique qu'au nombre
total de critères, pas au nombre de tests de navigateur.

**Et si un critère se révèle malgré tout indémontrable**, la remontée au citizen developer a une forme
obligatoire : au moins deux options, formulées en résultats observables, avec ce qu'il perd dans chaque
cas. Si l'agent ne sait pas produire deux options ainsi formulées, ce n'est pas un HITL checkpoint, c'est
un break-glass.

Règles associées :

- **Identifiants stables** (`DOD-1`, `DOD-2`…), jamais réutilisés. Ils portent le pont vers les tests (L3)
  et le référencement dans les attestations.
- **Fichier committé**, attaché à la PR. Chez Akria les artefacts de run sont gitignorés — cohérent
  puisque l'enforcement y vit dans les hooks locaux ; ici il vit dans la CI, qui ne voit pas un fichier ignoré.
- **Pas de borne dure sur le nombre total**, mais un signal en `warning` : un ou deux critères pour une
  fonctionnalité applicative laisse soupçonner du vague, au-delà d'une quinzaine la demande devrait être
  découpée. La seule borne dure porte sur les critères *démontrés par E2E* — cinq au plus, voir ci-dessus.
- **Immuable après validation.** Un critère qui se révèle infaisable est un blocage métier : retour au
  citizen developer, jamais une réécriture silencieuse. Toute modification crée une révision datée et
  motivée, et redemande validation. Transposition du *scope reduction = hold* d'Akria — c'est ce qui
  empêche l'agent de rétrécir la cible pour atteindre le vert.

#### Règle de partage avec les guardrails

> **Invariant permanent → guardrail, jamais dans la DoD. Contrainte propre à la demande → acceptance
> criterion.**

« Le SQL est paramétré », « tout appel HTTP a un timeout », « une migration accompagne tout changement de
modèle » sont vrais pour toutes les demandes : les recopier dans chaque DoD noierait sous du bruit
incompréhensible les trois lignes qui comptent. « L'export tient jusqu'à 10 000 lignes », « aucune donnée
nominative dans le fichier produit » sont propres à cette demande : hors du contrat, personne ne les
vérifiera.

Conséquence pour la non-régression des apps interactives — `data/interactive/` importe `lib.query`,
`web.db`, `web.config`, et un renommage anodin dans `lib/` casse des tableaux de bord en production :
c'est un **guardrail permanent** (fitness function, L6), pas un critère. Il protège ainsi aussi les
changements qui ne passent pas par le paved road.

#### Règles de sélection des sources

Pas de liste fixe de documents à lire : la demande détermine les sources. L'agent décide seul, mais sa
décision est traçable — chaque source lue s'explique par une règle déclenchée.

Distinction préalable, souvent confondue : les **sources de données métier** (Zendesk, Metabase, RPE)
servent à *répondre à une question d'analyse*, jamais à *spécifier une feature d'Autometa*. Les tickets
Zendesk parlent des Emplois de l'Inclusion, pas de ce logiciel.

| Règle | Déclencheur | Ce qu'elle évite |
|---|---|---|
| **R1** | Toujours : le code existant de la surface nommée | Spécifier ce qui existe déjà à moitié, et produire une preuve verte sans avoir rien fait |
| **R2** | Un critère porte un chiffre → citer sa source de mesure | « 10 000 lignes en 30 s » alors qu'aucun rapport ne dépasse 500 lignes. Un nombre sans provenance est une invention, et il contamine jusqu'à la preuve censée le démontrer |
| **R3** | La demande emploie un terme du glossaire (pass, prescripteur, activation, adoption…) → `knowledge/bizdev/glossaire.md` | Réutiliser un mot métier avec le mauvais sens |
| **R4** | La surface est importée par `data/interactive/` (`lib.query`, `web.db`, `web.config`) → lister les TDB concernés | Casser des tableaux de bord en production sans le savoir |
| **R5** | Le sujet apparaît dans `docs/plans/` → lire la décision passée | Re-trancher une question déjà tranchée, dans l'autre sens |
| **R6** | La demande porte sur l'usage réel du produit → conversations Autometa en base | Concevoir pour un usage supposé |

R1 et R2 sont les seules inconditionnelles, et ce sont elles qui portent le bénéfice : le pire gaspillage
est de construire ce qui existe déjà, et un critère chiffré inventé fausse tout l'aval.

#### Dispositif anti-complaisance

Un agent qui rédige ses propres critères d'acceptation rédige des critères qu'il sait satisfaire : c'est
« juge et partie » déplacé en amont. Le dispositif d'`akria-pipeline` est repris intégralement, avec une
inversion.

| Mécanisme | Effet |
|---|---|
| **Self-grill contre la source de vérité** | Les critères se dérivent des sources sélectionnées par les règles ci-dessus. Ce qu'une lecture peut trancher devient une assertion réfutable, pas une question posée |
| **Questions ouvertes vides** | Le « quoi » se fixe ici et nulle part ailleurs : toute ambiguïté restante est portée dans une section dédiée, et sa présence est ce qu'un check sait constater — pas son contenu (voir « L0 n'est pas un guardrail ») |
| **`gap-hunter`** | Lentille adversariale : pour chaque comportement décrit, que se passe-t-il si l'entrée est invalide, vide, dupliquée, concurrente, hors limites ? Le silence est un trou |
| **`reverse-translation` inversée** | Voir ci-dessous |
| **Défaut BUSINESS** | Un défaut technique, l'agent le corrige seul ; une ambiguïté de périmètre ou des critères vagues remontent au citizen developer. **En cas de doute sur la catégorie, on classe BUSINESS** — demander vaut mieux que réécrire silencieusement le contrat |
| **Preuve de balayage** | Chaque lentille liste ce qu'elle a réellement lu ; une review superficielle devient visible |
| **Re-validation** | Après correction, la lentille qui avait bloqué est re-dispatchée et doit revenir propre |

**L'inversion de `reverse-translation`.** Chez Akria, cette lentille est un contrôle *interne* : un agent
retraduit la spec en langage clair, un autre compare à l'intention d'origine, et le résultat finit dans un
champ YAML que personne ne lit. C'est cohérent là-bas, où l'humain de la boucle est technique et lit la spec
directement.

Ici, la retraduction **est l'interface**. C'est le seul texte que lit le citizen developer, et sa validation
fait gate. La lentille ne produit donc plus un verdict machine mais un texte qu'une personne non technique
peut réfuter.

Ces sept mécanismes s'appliquent **à L0 seulement**. La friction se concentre là où une erreur coûte tout
l'aval ; le ratchet reste la règle pour les niveaux supérieurs.

#### Budget d'interaction : cinq décisions, pas un questionnaire

Les sept mécanismes convergent tous sur l'unique moment où l'on sollicite le citizen developer, et deux
d'entre eux fabriquent mécaniquement des questions techniques. `gap-hunter` interroge, pour chaque
comportement décrit, l'entrée invalide, vide, dupliquée, **concurrente**, hors limites ; le défaut
BUSINESS impose de remonter en cas de doute. Sur l'exemple de l'export PDF, cela donne « que doit-il se
passer si deux personnes exportent le même rapport en même temps ? » — une question de concurrence, que
le design interdit ailleurs en toutes lettres. Le garde-fou prévu (« ce qu'une lecture peut trancher
devient une assertion réfutable ») ne couvre pas les trous qu'aucune lecture ne tranche, et rien
n'empêche la session unique de devenir un questionnaire de vingt items — la forme classique de la
non-adoption.

D'où une contrainte de format sur la restitution :

- **Au plus cinq décisions** soumises au citizen developer, chacune avec un **défaut déjà choisi** et sa
  conséquence observable en français. Validation par exception : ne rien dire, c'est accepter le défaut.
- Ce que `gap-hunter` trouve au-delà devient un `DOD-N` **proposé avec sa valeur par défaut**, pas une
  question posée.
- Aucune question dont la réponse ne change rien d'observable pour lui ne remonte. Si elle ne modifie
  aucun critère, elle relève du défaut technique, que l'agent tranche seul.

#### L0 n'est pas un guardrail, et n'en sera jamais un

Il faut le dire explicitement, sous peine d'incohérence : l'élément déclaré irréductible du design est
porté par l'anneau qui, par définition, ne garantit rien. Les sept mécanismes ci-dessus sont des lentilles
de sous-agent, donc des Adapters. La garantie de L0 est **humaine** — c'est la validation du citizen
developer, et rien d'autre.

Ce qu'un exécutable peut vérifier ici est court, et c'est tout ce qu'on lui demande : le fichier existe, le
format `DOD-N` est respecté, les identifiants sont uniques et jamais réutilisés, le nombre de critères est
dans les bornes (signal en `warning`), la section des questions ouvertes est présente. En revanche « un
check refuse de sceller L0 si des ambiguïtés subsistent » ne veut rien dire côté machine : il constate une
section vide, pas une absence d'ambiguïté, et l'agent vide une section en une ligne.

Un point mérite mieux qu'une convention, parce qu'il est vérifiable pour rien : **l'antériorité**. « Un
accord écrit avant de coder » n'est prouvé par aucun mécanisme — DoD et code arrivent dans la même PR, et
l'attestation démontre la correspondance au contenu, jamais l'ordre. Un check l'établit : le premier commit
de la branche est celui qui ajoute `definition-of-done.md` (`git log --diff-filter=A`). Coût nul, incident
prévenu — une DoD rédigée après coup pour coller au code déjà produit, c'est-à-dire le retour exact du
« juge et partie » que L0 est censé supprimer.

#### Dette assumée

La validation du citizen developer n'est **pas** matérialisée par une preuve infalsifiable — une mention
dans le fichier suffit, que l'agent pourrait écrire lui-même. C'est le seul point de L0 qui reste
auto-déclaratif, et c'est un choix délibéré contre la friction initiale.

Déclencheur de durcissement : la première fois qu'une DoD apparaît validée sans que le citizen developer
se souvienne de l'avoir lue, le friction log le capte et la validation passe par une draft PR ouverte dès
L0, où l'approbation GitHub fournit une trace horodatée, attribuée et hors de portée de l'agent.

### L1 — Attestation

Un state journal par branche et une commande d'avancement. L'état ne progresse que si de vraies commandes
sortent en 0 : **le verdict provient des codes de sortie, jamais d'une phrase de l'agent.** C'est l'unique
mécanisme d'`akria-pipeline` repris intégralement (`advance`), parce qu'il rend la dérive silencieuse
structurellement impossible sans coûter de friction.

Le terme est emprunté à SLSA / in-toto : une attestation est une métadonnée *authentifiée* sur un
artefact — un reçu, pas une affirmation.

**L'emprunt est partiel, et il faut le dire.** Le rattachement au contenu prouvé traite la *péremption*,
pas la *fabrication* : un fichier écrit à la main porte les bonnes empreintes. Ce que L1 garantit est donc
plus étroit que ce que le mot suggère — **plus aucun PASS sans code de sortie 0**, l'evidence
comportementale restant déclarative jusqu'à L3, où elle devient la sortie d'un test rejouable.

Deux conséquences dans le plan. La CI qui lit ces attestations (milestone 4) ne leur fait pas confiance :
elle **rejoue** les checks et compare son propre résultat au verdict journalisé, tout écart devenant un
échec. Le journal redevient ce qu'il est, un cache et une source de statistiques, et cesse d'être une
autorité. Et le décalage entre L1 (milestone 3) et L3 (milestone 5) est assumé plutôt que masqué : dans
cet intervalle, la garantie porte sur l'exécution des commandes, pas sur ce que l'agent en raconte.

Quatre verbes suffisent — démarrer, consulter l'état, lancer les checks, avancer — exposés comme cibles
du `Makefile` existant, donc invocables par n'importe quel agent, par la CI, ou à la main.

#### Rattachement au code : le contenu prouvé, ni la date ni le commit

Akria compare des dates de fichiers (`smoke-evidence` : les captures doivent être plus récentes que
`verify-report.yaml`). Insuffisant ici : l'agent dispose de Bash, et `touch` rend n'importe quelle capture
« fraîche ». Une date de fichier n'est pas une attestation, c'est une affirmation horodatée.

Le SHA de HEAD ne convient pas davantage, pour une raison mécanique : **l'attestation est committée par
construction, et ce commit déplace HEAD.** Produite à `HEAD=A`, rangée, la CI lit `B` et une attestation
qui annonce `A` : elle est fausse à la seconde où on la classe. Re-prouver produit un nouveau commit, donc
une nouvelle invalidation — la boucle ne termine pas. S'y ajoute le rebase, obligatoire ici (historique
linéaire sur `main`, 110 commits en 90 jours) : il réécrit tous les SHA d'une branche dont le code n'a pas
bougé d'une ligne.

**Chaque attestation enregistre les empreintes d'arbre des chemins qu'elle prouve** — `git rev-parse
HEAD:web`, `HEAD:lib`, `HEAD:alembic`, le dossier du TDB concerné — à l'exclusion du dossier
d'attestations et du journal. Le check passe si ces arbres sont inchangés ; l'équivalent opérationnel est
`git diff --quiet <réf attestée> HEAD -- <chemins prouvés>`.

Conséquences : ranger la preuve et rebaser deviennent neutres, une vraie modification du code invalide
toujours, et l'attestation reste vérifiable par quiconque — CI comprise — sans faire confiance à l'horloge
ni au système de fichiers. La règle d'exclusion doit être écrite noir sur blanc dans l'implémentation :
sans elle, on reproduit la boucle.

#### Granularité : une attestation par critère

Chaque `DOD-N` porte la sienne : la commande lancée, son code de sortie, les empreintes d'arbre des
chemins prouvés, et un verdict démontré / non démontré. Un critère non démontré ne peut donc pas se noyer
dans un rapport global. Le récapitulatif en français n'est pas dupliqué ici : il est produit par la
description de PR à partir de ces attestations.

#### Ce qu'une attestation ne contient jamais

**Le dépôt est public.** Le produit manipule des données sur des demandeurs d'emploi — il embarque
d'ailleurs un module d'anonymisation dédié (`lib/pii.py`) précisément parce que du texte réel transite.
Or le design fait committer quatre artefacts nés de l'exécution réelle : DoD, journal, attestations,
captures. Le raisonnement qui impose de les committer est correct (la CI ne voit pas un fichier ignoré),
mais il ne dit rien de leur contenu, et aucun des sept niveaux ne le regarde : ils vérifient la fraîcheur
et le verdict. `gitleaks` cherche des motifs de secrets, pas des noms de personnes, et n'ouvre pas une
image. Paradoxe propre à ce design : plus il produit de preuves, plus il expose — dans un historique git
public, qui ne s'efface pas.

> Sous `attestations/`, **uniquement ce qu'`advance` produit seul** : commande, code de sortie, sortie
> tronquée, empreintes, verdict. Aucune image, aucun binaire, aucune sortie brute de requête.

Un check le refuse, directement bloquant : le faux positif coûte un renommage de chemin, le faux négatif
est irréversible. Les captures produites en L4 transitent par les artefacts de CI ou un commentaire de PR,
hors dépôt. Le champ narratif « ce qui a été observé » disparaît de l'attestation — il appartient au
friction log, qui n'a ni la même autorité ni la même durée de vie.

#### États et journal

Trois états, alignés sur les trois temps du parcours : `align`, `build`, `prove`. Le journal est **committé**
— la CI porte les guardrails et ne verrait pas un fichier ignoré. Seul `advance` y écrit, et seulement
d'après des codes de sortie réels.

**Un répertoire, pas un fichier.** Le conflit de rebase n'est pas seulement un désagrément assumé : sur un
journal mono-fichier append-only, sa résolution est une écriture manuelle par l'agent, hors `advance` et
sans code de sortie — ce qui casse l'invariant dont L1 tire toute son autorité. Le tableau des familles
d'échec l'autorise d'ailleurs explicitement, en rangeant « rebase à faire » dans le travail normal. Or le
rebase est ici obligatoire (historique linéaire sur `main`) et fréquent. Le journal est donc un répertoire
d'événements — un fichier par événement, nommé par horodatage et empreinte courte, agrégé à la lecture.
Git ne conflicte jamais sur des fichiers distincts, `advance` reste seul écrivain, et le rebase devient
inerte sur le journal comme sur les attestations.

#### Échecs : tri par famille, pas compteur

Akria force une pause au troisième échec consécutif. Un compteur brut est un mauvais outil, parce que les
échecs n'appellent pas la même réponse :

| Famille | Causes | Réponse |
|---|---|---|
| **A. Réparable** | test rouge, lint, couverture sous le seuil, attestation invalidée par une modification du code, rebase à faire | L'agent réessaie — c'est le travail normal, dans la limite du plafond ci-dessous |
| **B. Environnement** | Postgres ou Redis absent, Matomo ou Metabase indisponible, réseau | Arrêt immédiat, signalé comme panne. Réessayer brûle du temps sans rien corriger |
| **C. Question métier** | critère ambigu, critère infaisable découvert tard, périmètre flou | Retour au citizen developer — HITL checkpoint |
| **D. Interdit** | tentative d'abaisser un seuil, migration destructive, suppression de test | Break-glass |

Réessayer sur A est légitime et fréquent ; réessayer sur B, C ou D est une erreur dès la première fois.
Chaque check déclare donc sa famille, et c'est elle qui commande la suite — pas un seuil.

#### Une borne quand même, sur la famille A

Écarter le compteur d'Akria ne veut pas dire ne rien mettre à la place. La famille A n'a aujourd'hui aucun
plafond de tentatives, aucun budget mural, aucun budget de tokens — et deux autres décisions l'amplifient :
le travail se fait en AFK, donc sans garde-fou humain, et une correction qui touche le code invalide les
preuves qui en dépendent, y compris une passe de smoke qui coûte plusieurs centaines de milliers de tokens.
Un vendredi soir, cela donne : corriger un test, re-prouver, échouer ailleurs, corriger, re-prouver — et
une facture le lundi sans que rien n'ait avancé.

Le produit possède déjà le mécanisme qui manque, visiblement construit après un incident : `MAX_TOOL_CALLS`
et son avertissement intermédiaire, appliqués dans `web/runner.py`, annulent un backend qui s'emballe. Il ne
protège que les conversations du produit — l'agent du paved road tourne ailleurs.

Le plafond de tentatives par état ne produit donc pas un échec mais une **conversion en HITL checkpoint** :
le mécanisme existe déjà, et l'asymétrie est respectée puisque l'agent se met en pause sans se débloquer.
Il entre en observation au milestone 3 — `advance` journalise le compteur sans agir — pour que la valeur du
plafond soit choisie sur les données du milestone 1 plutôt que devinée aujourd'hui.

Une précision sur le coût des re-preuves, maintenant que l'attestation est rattachée au contenu : un commit
qui ne touche pas les chemins prouvés n'invalide plus rien. Restent les corrections réelles, qui doivent
invalider. Pour les preuves déterministes, rejouables et bon marché, la règle s'applique sans réserve ;
pour la passe de smoke, non déterministe et coûteuse, une seule passe est exigée, sur le dernier état du
code avant ouverture de la PR.

### L2 — Quality Gates

Ce niveau protège **tout le monde** — paved road ou pas, Claude ou Codex, humain ou cron.

#### Le trou principal n'est pas dans la CI, il est dans son branchement

`main` est protégée : force-push interdit, historique linéaire, suppressions bloquées, admins inclus, push
direct fermé. Mais l'API ne renvoie **ni `required_status_checks`, ni `required_pull_request_reviews`**.

Conséquence : la CI est complète et rien n'oblige qu'elle soit verte pour merger. Une PR rouge se merge
aujourd'hui sans obstacle, et le fait est constaté : le 2026-08-05, la CI est en échec sur `main` pendant
que `Deploy staging` et `Deploy prod` passent au vert sur le même commit. Le premier geste de L2 n'est donc
pas du développement mais des réglages GitHub, à effet immédiat sur tout le dépôt. Trois précautions
conditionnent leur succès, et chacune suffit à tout bloquer si elle est omise.

**Les noms des checks sont ceux publiés, pas les identifiants de job.** GitHub matche
`required_status_checks` sur le nom du check run. `ci.yml` déclare `name: Lint & format`, `Security`,
`Tests`, `Migrations`, `Docker` — ce sont ces cinq chaînes littérales qu'il faut inscrire. Un contexte
inconnu reste indéfiniment « Expected — Waiting for status to be reported », et `enforce_admins: true`
interdit de forcer le passage : toutes les PR seraient bloquées sans message d'erreur. À vérifier sur une
PR témoin par `gh api repos/:owner/:repo/commits/<sha>/check-runs` avant d'armer. Le head porte en outre
des checks tiers (`CodeQL`, `GitGuardian`) : les laisser non requis est un choix légitime, il doit être
écrit. Enfin, un contrôle compare la liste requise aux `name:` de `ci.yml` et échoue en cas de dérive —
sans lui, renommer un job éteint la protection en silence.

**`main` doit être au vert, et `pip-audit` doit sortir du gate bloquant.** Le job `Security` est en échec
depuis le 2026-08-05 sur une vulnérabilité annoncée dans une dépendance amont ; `ci.yml` porte déjà deux
`--ignore-vuln`, l'événement est récurrent et exogène. Le rendre bloquant enferme le dépôt, et le
déblocage passe par l'édition de `ci.yml`, que `CODEOWNERS` verrouille au même moment. `pip-audit` part
donc dans un job `Dependencies` nightly non requis ; `bandit` et `gitleaks`, qui portent sur le diff,
restent dans `Security` et restent bloquants.

**`strict: true`.** Sans ce drapeau, GitHub accepte de merger une PR dont la CI a été verte sur une base
périmée : chaque PR est individuellement verte, leur combinaison ne l'est pas. Cas concret, le seul mode
de défaillance qui naisse du fait qu'ils sont deux : deux branches ajoutent chacune une migration enfant
du même `down_revision`, les deux sont vertes, et `main` se retrouve avec deux heads Alembic. Coût réel :
un re-run de CI après rebase, ce que le travail en AFK absorbe.

Les deux réglages proprement dits :

- **`required_status_checks`** avec `strict: true` sur les cinq contextes littéraux ci-dessus.
- **`required_pull_request_reviews`** avec `require_code_owner_reviews` — sans quoi le `CODEOWNERS`
  ci-dessous reste décoratif. Ce réglage a un prérequis humain qui n'est pas un détail : voir « Qui merge ».

#### Trois angles morts de la CI existante, à traiter au même moment

Rendre la CI obligatoire n'a d'intérêt que si elle regarde ce qu'on croit qu'elle regarde. Trois écarts
sont mesurés, et se corrigent par de la configuration.

**`skills/` échappe à trois gates déjà payés.** Le lint en CI est restreint à `web/ lib/ tests/ scripts/`
alors que `make lint` couvre tout le dépôt — le local et la CI divergent ; l'analyse de sécurité exclut
`skills/` ; et la couverture ne le déclare pas comme source, si bien qu'un diff situé exclusivement dans
`skills/` ne présente aucune ligne au gate de 90 % et passe. Or il s'y trouve une trentaine de fichiers
Python, dont ceux qui écrivent en base et sur S3. C'est distinct du chantier différé sur les evals, qui
porte sur la qualité d'un `SKILL.md` en tant que prompt : ici il s'agit de code exécutable. Trois lignes de
configuration, avec mesure préalable de ce que ça fait remonter.

**Le job `Migrations` tourne sur une base vide**, donc toute migration dépendante des données y est verte
par construction. L'incident est déjà dans l'historique du dépôt : une migration a dû se voir ajouter sept
`UPDATE ... WHERE ... IS NULL` avant ses `alter_column`, avec le commentaire « sinon la migration échoue en
prod ». C'est le raisonnement qu'un citizen developer ne peut pas faire et que l'autogenerate ne fait pas.
À distinguer du chantier « migrations destructives » laissé en réserve, qui vise un DDL destructeur : ici
la migration n'est pas destructive, elle est invalide au contact de données réelles. Traitement : une
seconde passe contre un dump anonymisé de staging, en observation le temps d'établir le dump ; à défaut, un
signal sur toute migration posant une contrainte non nulle sans `op.execute` préalable dans le même
`upgrade()`.

**La CI ne passe pas par le `Makefile`**, elle réécrit chaque commande — et la dérive est déjà là : un CVE
ignoré d'un côté et pas de l'autre, des périmètres de lint différents. Tant que c'est le cas, « la CI
relance le même check » est faux, et ce sera vrai aussi des futures cibles `advance` et `checks`, qui sont
le pivot de l'anneau Core. La CI appelle les cibles du `Makefile`, les chemins et exclusions étant définis
une seule fois.

#### pre-push : un service, pas un guardrail

Un git hook se contourne avec `--no-verify`. Il ne peut donc pas porter de garantie — et le design pose
qu'un guardrail capable de s'éteindre silencieusement n'en est pas un. Le `pre-push` ne lance que ce qui
est rapide (lint, tests unitaires), pour éviter un aller-retour CI. La garantie réelle est la branch
protection, non contournable.

Un miroir complet de la CI en local a été écarté : trop lent à chaque push, donc contourné en pratique —
de la friction construite pour rien.

#### Auto-protection par CODEOWNERS

Sans elle, tous les autres principes s'effondrent en une session : il suffit à l'agent d'abaisser un seuil
ou de supprimer un test pour se débloquer.

Les fichiers de gate — seuils de couverture, workflows, hooks, configuration du paved road — sont couverts
par `CODEOWNERS` et exigent une approbation humaine. Mécanisme GitHub natif, aucun code à écrire ni à
maintenir. Il réintroduit une relecture humaine, mais sur un périmètre choisi pour ne jamais se déclencher
sur du travail applicatif ordinaire : c'est précisément le break-glass.

**Le bon critère n'est pas la taille du périmètre, c'est la fréquence de déclenchement.** Un `CODEOWNERS`
qui se réveille tous les jours produit des approbations en série sans lecture, ce qui vaut moins que pas
de `CODEOWNERS` du tout. Deux corrections en découlent, dans les deux directions.

*Retirer.* Les seuils vivent aujourd'hui dans `pyproject.toml`, c'est-à-dire dans le même fichier que les
dépendances — que Dependabot modifie quotidiennement, et qui totalise une cinquantaine de commits par an.
Les extraire vers un fichier dédié est un prérequis à la pose de `CODEOWNERS`, pas un raffinement. À noter
que GitHub exige une approbation **par règle matchée**, pas une au total : une PR qui bumpe une dépendance
et ajuste un workflow réveillerait deux fois le break-glass.

*Ajouter.* Le retrait de `.claude/rules/zones-critiques.md` est présenté comme un remplacement ; c'en est
un pour `data/interactive/` et pour les motifs d'import, pas pour le reste. Restent sans successeur
`web/db.py`, `web/runner.py`, `web/agents/base.py`, `web/uploads.py` — surface de sécurité nommée —,
`docker-compose.yml`, `Dockerfile`, `config/sources.yaml`, et les clients d'intégration externe
(`lib/matomo.py`, `lib/metabase.py`, `web/s3.py`, `web/notion.py`, `web/agents/cli.py`). Le design a raison
sur le diagnostic — une promesse de relecture que personne n'honore ne vaut rien — mais il retient ailleurs
le mécanisme qui convient exactement à ce besoin. Ces chemins rejoignent donc `CODEOWNERS` : sept lignes,
aucun code. Un citizen developer qui demande une fonctionnalité n'y touche pas ; quand il y touche, c'est
le break-glass revendiqué.

`web/models.py` et `alembic/` en sont volontairement **exclus** : une fonctionnalité applicative ordinaire
y atterrit trop souvent, et les y mettre reproduirait le défaut de `pyproject.toml`.

#### Deux modes de panne silencieux de CODEOWNERS

Le mécanisme est natif, il n'est pas pour autant sans angle mort, et ses deux défaillances sont muettes.

- Une entrée dont le titulaire n'a pas un droit `write` **explicite** est ignorée sans erreur : le gate
  n'existe pas, et rien ne le signale.
- Un ensemble d'owners réduit à une personne rend impossible toute PR de cette personne sur un fichier de
  gate, puisqu'un auteur ne s'auto-approuve pas et que `enforce_admins` est actif.

D'où : une équipe GitHub avec droit `write` explicite et au moins deux membres, et un appel à
`GET /repos/:owner/:repo/codeowners/errors` dans la CI, qui échoue si la réponse n'est pas vide. C'est le
seul moyen d'apprendre qu'un guardrail s'est éteint.

### L3 — E2E

L'evidence cesse d'être une capture produite par l'agent et devient un **test exécutable**, déterministe,
dérivé des acceptance criteria.

**Playwright, un test par `DOD-N`.** L'outil est un exécutable, donc dans le Core : rejouable par la CI,
par un humain, par n'importe quel agent, dans six mois. La preuve devient une sortie du système plutôt
qu'une production de celui qu'on juge.

Deux effets gratuits : la correspondance un-pour-un entre critères et tests — prévue à l'origine comme un
chantier de L6 — existe dès ce niveau et devient vérifiable mécaniquement ; et la protection dure dans le
temps. Un parcours joué une fois démontre ; un test entré dans la suite **défend**. Si quelqu'un casse
l'export trois mois plus tard, `test_dod_1` devient rouge tout seul, sur la PR du coupable.

**Mais cette promesse est prospective, et son corollaire doit être tiré.** Au jour 1, aucune fonctionnalité
existante ne porte de `DOD-N` : la suite est vide et ne défend rien. Elle ne deviendra réelle qu'après
plusieurs fonctionnalités passées par le paved road, et ne couvrira jamais l'existant. Dans l'intervalle,
ce qui protège est une suite de tests unitaires — aucun parcours de navigateur — un plancher de couverture
qui ne bouge pas quand un comportement change à couverture constante, et un gate de diff qui ne mesure que
les lignes modifiées, donc jamais la fonctionnalité victime. Le design fait précisément ce raisonnement
pour les tableaux de bord ; il vaut aussi pour l'application, où le couplage est plus dense.

D'où **trois à cinq tests de socle écrits avant le premier test `DOD-N`** : connexion, création d'une
conversation, ouverture d'un rapport, page `/interactive/`, `/selftest`. Le coût marginal est nul —
l'infrastructure est de toute façon à monter — et c'est ce qui rend la non-régression vraie dès la première
fonctionnalité au lieu de la dixième.

**Exécution : CI sur chaque PR, plus une passe nightly.** Le test est écrit pour tourner indifféremment
contre une URL locale ou une URL de review app, et il tourne **contre les deux** : le local donne un
verdict rapide et gratuit, la review app démontre l'application telle qu'elle est réellement déployée.
Point d'attention : le `up`/`down` des review apps sera migré dans la CI — ne pas construire de mécanisme
local qui serait jeté.

#### Accès aux review apps : un second mode d'entrée, pas une porte ouverte

Toute instance déployée est derrière oauth2-proxy et un login Google : `Procfile` lance l'application
derrière `start_with_oauth2_proxy.sh`, `.buildpacks` inclut le buildpack betagouv, `OAUTH2_PROXY_PROVIDER`
vaut `google` et `OAUTH2_PROXY_EMAIL_DOMAINS` restreint à `inclusion.gouv.fr`. L'identité vient
exclusivement d'un en-tête injecté par le proxy (`web/deps.py`). Le commentaire de `scalingo.json` le dit
sans ambiguïté pour les review apps : la redirection y est surchargée « so login redirects back to the
review app ». Un navigateur piloté n'a pas de compte Google.

L'URL n'est pas l'obstacle — le motif `autometa-staging-pr<N>.osc-fr1.scalingo.io` se dérive de
`github.event.number`. C'est l'authentification.

**Décision : le proxy accepte un second mode d'entrée par secret technique**, connu du seul runner de CI
et stocké dans les secrets GitHub, activé sur les seules review apps (`AUTOMETA_ENV=review`). Un visiteur
humain voit toujours l'écran Google ; la review app n'est à aucun moment consultable depuis internet.
L'option consistant à dispenser certaines routes d'authentification a été écartée : elle rendrait ces
pages publiques pendant toute la vie de la review app, pour un gain de configuration marginal.

Prérequis à lever avant le milestone : le buildpack betagouv indique que « toute configuration
supplémentaire d'oauth2-proxy peut se faire par variables d'environnement », donc le mécanisme est
atteignable ; reste à valider que le fichier de secrets peut être produit au démarrage de l'instance.
Tant que ce point n'est pas levé, L3 et L4 tournent en local uniquement.

Rien de tel n'existe aujourd'hui dans le dépôt : Playwright est à introduire, avec un job CI dédié
(Postgres, Redis, stockage objet, application lancée, installation du navigateur) et un marqueur exclu du
filtre du job `Tests`. C'est le seul vrai chantier technique de ce niveau, et il n'entre pas dans
`required_status_checks` tant qu'il n'a pas prouvé son absence d'instabilité — le ratchet du design,
appliqué à son propre outillage.

### L4 — Smoke

Le pendant exploratoire de L3, et son complément exact : là où l'E2E vérifie ce qui était prévu, le smoke
attrape **ce que personne n'avait pensé à tester** — le bouton présent mais illisible, la page qui rame,
le PDF techniquement conforme et visuellement raté.

Piloté via MCP, en local puis sur la review app — par le même second mode d'entrée que L3 (voir ci-dessus),
donc conditionné au même prérequis. Non déterministe, non rejouable, dans les Adapters — et ici ce n'est
pas un défaut : on ne lui demande pas de garantir, on lui demande de regarder. Son adaptabilité est
précisément ce que la rigidité d'un test ne sait pas faire.

| | Public | Produit | Rôle |
|---|---|---|---|
| **E2E** (L3) | la machine | un verdict rouge ou vert | bloque, et défend dans la durée |
| **Smoke** (L4) | le citizen developer | des captures, un parcours réel | montre, et découvre l'imprévu |

C'est le poste de dépense dominant du design — un parcours d'une dizaine d'étapes coûte plusieurs centaines
de milliers de tokens d'entrée, l'essentiel venant des captures. Deux bornes en découlent, sans rien retirer
à ce qu'il apporte. Une seule passe par PR, sur le dernier état du code avant ouverture (voir L1). Et un
déclenchement restreint aux PR qui touchent une interface — templates, statiques, une route : ailleurs, un
parcours de navigateur ne peut rien révéler que les autres niveaux ne voient déjà.

#### Frontière

Le paved road est un **workflow de développement** : il s'achève à l'ouverture de la PR. Ce qui suit le
merge — déploiement staging, vérification post-deploy, promotion en production — est hors périmètre. Voir
l'annexe.

### L5 — Adversarial Review

Une lentille LLM n'est pas un exécutable reproductible : elle ne peut donc pas vivre dans les Guardrails.
Elle est lancée **dans le flot, par un sous-agent**, et appartient aux Adapters — elle améliore le
résultat, elle ne garantit rien formellement.

**Une seule lentille au démarrage : `design-coherence`** — le code fait-il ce que la DoD dit, ni plus ni
moins ? C'est la seule question qu'aucun autre niveau ne pose : `lint`, `bandit`, `gitleaks` et le gate de
couverture ne savent rien de l'intention. Sans DoD (L0) elle n'aurait d'ailleurs aucun référentiel et se
réduirait à du commentaire de style.

Les suivantes s'ajoutent une par une, quand le friction log les réclame. Catalogue de réserve, issu des
neuf lentilles du stage `review` d'Akria et des besoins propres à ce dépôt :

| Lentille | Mission | Origine |
|---|---|---|
| `abstraction-quality` | Sur-abstraction (factory pour un seul appelant) ou sous-abstraction (logique dupliquée, dépendance en dur) | Akria |
| `surgical-changes` | Changements sans lien avec la demande : reformatage opportuniste, refactor adjacent, suppression de dead code non demandée | Akria |
| `test-quality` | Assertions sur des mocks plutôt que sur un comportement, assertions faibles, happy path seul | Akria — recoupe `check_test_quality.py` |
| `edge-case-hunter` | Null, collections vides, valeurs limites, doublons, concurrence | Akria |
| `security-auditor` | Autorisation, injections, secrets, PII dans les logs | Akria |
| `legal-compliance` | RGPD et domaine IAE | Akria, adapté du domaine HSE |
| `dod-test-fidelity` | Un test marqué `DOD-N` est bien un parcours réel, pas un test unitaire déguisé | Équivalent de `tag-fidelity` (minter) |
| `query-cost` | Segments Matomo à 30-180 s, jamais plus de 5 requêtes segmentées en boucle — un agent tombe dedans naturellement | Propre au dépôt |
| `knowledge-drift` | `knowledge/` diverge du code ; `MAINTENANCE.md` le liste comme tâche trimestrielle jamais faite | Propre au dépôt |

Deux besoins souvent cités n'apparaissent pas ici, parce qu'ils sont largement automatisables : la
conformité aux `.claude/rules/` relève de L6, la sûreté des migrations de L2 — validation contre des
données réelles, pas jugement d'un modèle. Une lentille LLM qui vérifie ce qu'un `grep` fait mieux est du
gaspillage.

#### L'exception à la mise en réserve : la protection des routes

Une lentille `auth-audit` figurait dans ce catalogue. Elle en sort, et elle ne passe pas par le ratchet.

L'autorisation n'est pas posée une fois pour toutes dans cette application : elle est écrite **route par
route**, à la main (`web/deps.py` tire l'identité d'un en-tête de proxy, sans dépendance d'authentification
partagée). Une route neuve naît donc sans protection, et il faut penser à la lui ajouter. Or le paved road
fait précisément écrire des routes à un agent, pour quelqu'un qui ne lit pas le code : « une page qui liste
les candidatures par structure » produit une route dans `web/`, qui est au cœur du périmètre. Aucun des
sept niveaux ne le verrait — L0 exclut les invariants permanents, L2 ne modélise pas la sémantique FastAPI,
L3 joue le parcours en tant qu'utilisateur autorisé donc il est vert, L5 démarre avec `design-coherence`
seule.

Le ratchet suppose qu'un premier incident soit rattrapable. Il l'est pour un lint bavard ou un test
capricieux ; il ne l'est pas pour une exposition de données de demandeurs d'emploi, où le premier
incident *est* l'incident. Et l'état n'est pas hypothétique : `web/routes/query.py` expose déjà un
`POST /query` qui exécute du SQL fourni par le client sur trois bases, sans dépendance d'authentification,
avec pour seul filtre une comparaison d'`Origin` qu'un appel dépourvu de cet en-tête traverse.

**Un check déterministe le remplace, dès le milestone 0** : toute fonction décorée `@router.<verbe>` doit
porter une dépendance d'authentification ou figurer dans une allowlist committée et couverte par
`CODEOWNERS`. Les routes actuellement non protégées forment une baseline gelée — le check bloque les
routes **neuves**, sans casser l'existant, et la baseline se résorbe ensuite. Une soixantaine de lignes,
aucune dépendance LLM, aucune friction pour qui demande une fonctionnalité. L'état de `POST /query` se
traite par ailleurs, indépendamment de ce design.

### L6 — Fitness Functions

Terme de Neal Ford (*Building Evolutionary Architectures*) : une règle exécutable qui mesure qu'un système
préserve les propriétés voulues à mesure qu'il change. C'est ici que se matérialise le versant
« vérificateur » de chaque paire décrite en mécanismes transversaux — l'instruction en prose reste, elle
n'est simplement plus seule à porter la règle. Deux chantiers structurants :

#### D'abord ce qui est déjà écrit ailleurs

La configuration ruff active déjà `E`, `F`, `W`, `I`, `G` — l'interdiction des f-strings dans les logs est
donc **déjà appliquée**. Mais plusieurs règles rédigées en prose dans `.claude/rules/` — ou implémentées
dans un hook qui ne tourne que sous Claude Code — correspondent à des règles ruff simplement pas activées :

| Règle en prose | Règle ruff | Mesuré sur le dépôt |
|---|---|---|
| Imports relatifs parents interdits | `TID252` | 0 violation |
| `except` nu interdit | `E722` | 0 violation |
| Tout appel HTTP a un timeout explicite | `S113` | 0 violation — mais portée partielle, voir ci-dessous |
| `httpx` exclusivement ; pytest et non `unittest` | `TID251`, configuré | à mesurer une fois configuré |
| `os.getenv` uniquement dans `web/config.py` | `TID251` + exemptions | 18 cas, dont 3 légitimes hors tests |
| SQL non paramétré interdit | `S608` | 18 cas → observation |
| `except Exception` sans `# Why:` | `BLE001` | 8 cas → observation |

Trois précisions, sans lesquelles l'implémentation part de travers.

**La formulation « jamais `requests`, `urllib`, `unittest`, `psycopg2` » est trop large.** `urllib.parse`
est importé dans une douzaine de fichiers et `psycopg2` est une dépendance déclarée, utilisée par un hook.
La règle réelle, lisible dans `.claude/hooks/check_python.py`, ne bannit que `urllib.request` et `urllib3`,
et autorise `psycopg2` dans `lib/data_inclusion.py`. Ce sont ces motifs-là qu'il faut recopier.

**Les exemptions ne se posent pas au fichier.** Pour `os.environ`, `web/config.py` et les tests s'exemptent
en bloc ; mais les trois cas légitimes restants — substitution de patterns dans un fichier de configuration,
passage de l'environnement complet à un sous-processus — s'exemptent **en ligne**, avec justification. Une
exemption au fichier rendrait `web/cron.py` et `web/agents/cli.py` aveugles à une vraie lecture de
configuration ajoutée plus tard, précisément là où elle serait la plus délicate.

**`S113` ne couvre pas la règle qu'elle prétend porter.** Elle voit un appel littéral sans timeout, pas un
client de session construit sans timeout puis réutilisé — vérifié : le motif passe. Or c'est exactement la
forme du dépôt : cinq modules construisent un client de session sans timeout et repassent `timeout=` à
chaque appel. Ils sont conformes, mais rien ne l'impose : un appel ajouté demain sur le client existant
passerait le lint, le pre-commit et la CI. Soit on impose `timeout=` au constructeur dans ces cinq fichiers
et on bannit le reste, soit on écrit que ce risque demeure — mais on ne présente pas `S113` comme la
fitness function de cette règle.

Ces règles deviennent bloquantes pour une vingtaine de lignes de configuration, dans une CI déjà branchée
et rendue obligatoire par L2. C'est le meilleur rapport effort/effet du design — à condition de ne pas
promettre une découverte : la mesure est déjà faite, et sur les trois premières lignes elle dit « rien ».
C'est un cliquet sain, pas un audit.

#### Puis la protection des tableaux de bord — par une façade, pas par une mesure

Pas de graphe d'imports général : quel seuil ? Un seuil arbitraire bloquerait du travail légitime tout en
laissant passer un renommage dévastateur à rayon nul.

Mais un blast radius ciblé sur `data/interactive/` ne suffit pas non plus. Un check statique ne voit que
deux types de cassure sur sept :

| Changement dans `lib/` | Vu par un check statique |
|---|---|
| Symbole renommé ou supprimé | oui |
| Signature modifiée | oui |
| Valeur par défaut ou type de retour changé | partiellement |
| **Comportement changé à signature identique** — dates en UTC au lieu de local, filtre appliqué par défaut, exception au lieu d'un `None` | **non** |
| Contrat de `POST /api/query` modifié (les TDB l'appellent en JS) | **non** |
| Colonne renommée dans `dashboard_storage` | **non** |

C'est la ligne en gras qui fait mal : le tableau de bord continue de tourner, il produit simplement des
chiffres faux. Aucune alerte ne se déclenche — `web/cron.py` ne remonte que les crashs.

**La cause racine n'est pas l'absence de détection, c'est le couplage.** Les apps interactives importent
directement `lib.query`, `web.db`, `web.config` : elles dépendent d'internes qui n'ont jamais promis d'être
stables. Tant que c'est le cas, chaque refactor est un risque et aucun check ne le couvrira entièrement.

D'où le choix : **une façade explicite et versionnée pour les tableaux de bord**, seul point d'entrée
autorisé. On cesse de courir après les cassures : on réduit la surface où elles peuvent se produire. La
façade devient un contrat, ses tests en sont la preuve, et modifier ce contrat devient un acte visible
plutôt qu'un effet de bord.

C'est le seul mécanisme du design qui protège quelque chose d'*extérieur* au paved road : les tableaux
de bord sont hors périmètre (ils naissent de l'usage du produit, pas d'une PR), mais le développement de
l'application, lui, peut les casser. La façade est donc une contrainte sur `lib/`, pas sur eux.

**Le check ne peut pas vivre dans la CI.** `data/` n'est pas versionné — `git ls-files data/` ne renvoie
aucun fichier, la négation `!/data/interactive/` du `.gitignore` étant inerte (git ne ré-inclut pas sous
un répertoire exclu), et les artefacts vivent sur S3 (`web/s3.py`, restaurés par `web/warmup.py`,
énumérés par `web/cron.py`). Un check branché sur un diff s'exécuterait donc sur un dossier vide et serait
vert à perpétuité : le défaut même reproché à l'ancre de worktree d'Akria, un guardrail qui s'éteint sans
bruit. L'exclusion ruff de `data/` est le moindre des deux problèmes.

Le contrôle s'applique aux deux moments où un tableau de bord passe réellement :

- **À l'écriture** — les skills `create_dashboard` et `update_dashboard` sont le passage obligé ; ils
  refusent un import hors façade.
- **À l'exécution** — `web/cron.py` refuse de planifier un `cron.py` qui importe hors façade, et alerte
  sur le canal Slack qui existe déjà. En observation d'abord : bloquer d'emblée casserait des tableaux
  de bord vivants.

Deux conséquences à traiter :

- Migrer les TDB existants vers la façade — opération sur S3, pas une PR. Compter d'abord combien il y
  en a réellement en production : le chantier ne s'engage pas sans ce nombre.
- `.claude/rules/code.md` prescrit actuellement aux apps interactives d'utiliser `lib.query`, `web.db` et
  `web.config` directement. Cette règle est à réécrire en même temps, sinon elle contredit la façade.

C'est le successeur de `zones-critiques.md` **pour les tableaux de bord** : non pas une liste de fichiers
assortie d'une promesse de relecture que personne n'honorera, mais une frontière que le code ne peut pas
franchir. Les autres zones du fichier supprimé se répartissent entre `CODEOWNERS` (L2) et les règles ruff
ci-dessus — la répartition doit être faite ligne à ligne, faute de quoi la suppression est une régression
déguisée en remplacement.

#### Le pont critère → test est déjà acquis

Prévu ici à l'origine, il est obtenu gratuitement en L3 : Playwright génère un test par `DOD-N`. Il ne
reste qu'à vérifier la correspondance, ce que fait la lentille `dod-test-fidelity`.

#### En réserve

Migrations destructives et dérive `knowledge/` — écrits quand le friction log les réclame. Le SQL
interpolé sort de cette liste : `S608` le couvre, en observation dès le milestone 0.

## Mécanismes transversaux

### Chaque règle est une paire : une instruction, un vérificateur

La protection des routes (L5) n'est pas un cas particulier, c'est l'instance la plus coûteuse d'un
pattern général. Toute convention de ce dépôt existe sous deux formes, et il lui faut les deux :

| | Forme | Anneau | Ce qu'elle fait | Ce qu'elle ne fait pas |
|---|---|---|---|---|
| **Instruction** | prose dans `.claude/rules/`, un skill, un prompt | Adapters | l'agent produit du code conforme **du premier coup** | obliger — un agent peut l'ignorer, un autre agent ne la lit pas |
| **Vérificateur** | règle de lint, check AST, test | Guardrails | refuser ce qui n'est pas conforme, **quel que soit l'auteur** | guider — il ne dit qu'après coup, au prix d'un aller-retour |

C'est la distinction paved road / guardrail du design, appliquée au grain de la règle plutôt qu'au grain
du parcours. Les deux formes ne font pas double emploi : sans instruction, l'agent découvre la règle en
échouant, ce qui se paie en allers-retours et en tokens sur chaque run ; sans vérificateur, la règle est
auto-déclarative, et le design pose déjà que c'est nul et non avenu.

> **Une règle qui n'existe qu'en prose n'est pas une règle. Un vérificateur qui ne tourne que dans
> l'agent n'est pas un guardrail.**

#### Le travail est déjà fait, il est du mauvais côté

Le constat sur ce dépôt n'est pas qu'il manque des vérificateurs, c'est qu'ils sont mal placés.
`.claude/hooks/check_python.py` en implémente une douzaine — docstrings, commentaires descriptifs, code
commenté, imports bannis, `os.getenv`, `except` nu, `except Exception` sans `# Why:`, SQL non paramétré,
instanciation directe de `MatomoAPI`/`MetabaseAPI`, `httpx` sans timeout, nommage de module. Tous
s'exécutent **à l'écriture, sous Claude Code uniquement**. Ce sont d'excellentes instructions armées et
de faux guardrails : un autre agent, un humain pressé ou un `git commit` en ligne de commande n'en voient
rien.

Répartition réelle des conventions du dépôt :

| Où vit la vérification | Exemples | Compte |
|---|---|---|
| **Guardrail** — CI, hors agent | f-strings dans les logs (`ruff G`), migration accompagnant un modèle (`alembic check`), secrets en dur (`gitleaks`), test sur le code modifié (`diff-cover` à 90 %) | 4 |
| **Adapter** — `check_python.py`, Claude Code seul | la douzaine ci-dessus | ~12 |
| **Rien** | route sans protection (`review.md` la liste pourtant en critère de rejet), plus de cinq requêtes segmentées Matomo, marqueur `integration` | 3 |

#### La règle opératoire

Chaque entrée de `.claude/rules/` déclare où vit sa vérification. Trois réponses admises : une règle de
lint, un check déterministe nommé, ou *aucune* — et dans ce dernier cas c'est écrit, pas sous-entendu.
« Vérifié par un hook Claude Code » n'est pas une réponse recevable ; c'est une instruction bien outillée,
qui reste dans les Adapters.

Le déplacement coûte peu, et il est chiffré en L6, règle par règle. Deux principes en découlent, qui ne
dépendent pas de ces chiffres. Une règle passée côté Guardrail **sort de `check_python.py`** : deux
implémentations de la même règle divergent toujours, et elles divergent déjà. Et une règle dont le
vérificateur remonte des cas légitimes entre en observation plutôt que d'être écartée — c'est à cela que
sert la phase d'observation du ratchet.

Le cas de la protection des routes est le plus cher parce qu'il est dans la troisième ligne du tableau —
l'instruction existe, aucun vérificateur ne l'accompagne — et parce que son premier incident n'est pas
rattrapable. C'est ce qui le sort du ratchet, pas sa nature.

### The ratchet

```
   un incident réel  ──▶  friction log  ──▶  nouveau check
                                                   │
                                                   ▼
                                         ┌──────────────────┐
                                         │  warning         │  il rapporte,
                                         │  (observation)   │  il ne bloque pas
                                         └────────┬─────────┘
                                                  │  zéro faux positif
                                                  ▼  sur N runs
                                         ┌──────────────────┐
                                         │  blocking        │  et ne redescend
                                         │                  │  jamais
                                         └──────────────────┘
```

Tout nouveau check entre en observation. Il ne devient bloquant qu'après avoir prouvé qu'il ne produit
pas de faux positifs, et ne redescend jamais — même principe que le plancher de couverture déjà gelé dans
ce dépôt.

**La décision de passage est humaine, prise sur données.** Le jugement reste là où il a de la valeur ; il
ne s'exerce pas à vide.

Ces données ne viennent pas du journal, et c'est un point à ne pas confondre : le journal est local à une
branche et seul `advance` y écrit, alors que les checks appelés à devenir bloquants — ceux de L2 et de L6 —
tournent en CI, qui n'a pas le droit d'écrire dans le dépôt. Le comptage des faux positifs d'un check en
observation s'y trouverait donc absent. Il se prend là où il existe déjà : les conclusions et annotations
des check runs GitHub, interrogeables sans écrire une ligne de code. Le critère de promotion devient « N
exécutions consécutives sans annotation de ce check sur des PR finalement mergées » — mesurable
rétroactivement, et indépendant de ce que l'agent déclare.

Le journal garde son rôle propre : les familles d'échec du parcours, côté agent, qui alimentent le
milestone 1.

Conséquence directe : **on ne décide pas aujourd'hui du niveau de contrainte final, on décide de la
trajectoire.** Aucune contrainte n'est ajoutée par anticipation ; un check n'existe que parce qu'un
incident l'a réclamé. Les vingt verifiers d'`akria-pipeline` ne sont pas nés d'un design mais de vingt
incidents ; les copier d'emblée reviendrait à payer leurs cicatrices sans avoir eu leurs blessures.

### The friction log

Une rétro écrite par l'agent à la fin de chaque run : où il a tourné en rond, ce qui manquait dans le
contexte, quelle règle l'a gêné sans raison, quelle contrainte lui a manqué. Périodiquement, une friction
se convertit en check.

Le choix de la rétro narrative est assumé : elle capte ce qu'aucun gate n'a vu — et c'est précisément là
que se trouvent les frictions dont on ignore encore l'existence. Sa subjectivité est compensée par la
séparation des rôles : **la rétro fournit la matière, le journal fournit les chiffres.** Aucune décision
de cliquet ne repose sur le récit de l'agent.

### HITL checkpoint contre break-glass escalation

`akria-pipeline` confond les deux sous une catégorie unique « defer », qui suppose un humain technique
disponible. Ici la distinction est structurante :

| Nature | Exemple | Qui peut lever |
|---|---|---|
| **HITL checkpoint** | « un pass IAE vaut-il 2 ans ou 24 mois glissants ? » | le citizen developer, en français |
| **Break-glass escalation** | l'agent ne peut pas garantir sans décision d'ingénierie | personne dans la boucle — c'est l'exception mesurée |

Poser une question technique à une personne non technique produit soit un blocage définitif, soit une
validation à l'aveugle. Les deux sont pires que l'arrêt annoncé.

L'asymétrie d'`akria-pipeline` est conservée : l'agent peut se mettre en pause, il ne peut jamais se
débloquer lui-même.

### La matrice de preuve

Pas de voie rapide, pas de dispense. **Le rituel est identique pour tout fichier ; c'est la nature de la
preuve qui change.** Un `SKILL.md` n'échappe pas au parcours — il n'est simplement pas prouvé par un lint
Python.

Le découpage « fast path / full path » a été écarté pour cette raison : il crée une catégorie de fichiers
dispensés, et la dégradation s'y installe exactement parce que personne ne la regarde.

À ne pas confondre avec le déclencheur de périmètre : celui-ci dit **quand** une PR entre dans le paved
road, la matrice dit **comment** chaque fichier s'y prouve une fois qu'elle y est. Une PR qui touche
`web/` et met à jour `docs/` au passage relève des deux lignes ; une PR qui ne touche que `docs/` n'entre
pas dans le parcours.

| Artefact modifié | Preuve déterministe | Preuve comportementale |
|---|---|---|
| `web/`, `lib/` | lint, tests, couverture 90 % du diff | E2E Playwright, un test par `DOD-N`, cinq au plus |
| `alembic/` | `alembic check`, migration jouée sur données réelles | — |
| `skills/*/SKILL.md` | frontmatter valide, chemins et scripts cités existants | *différé* — evals sur golden set |
| `knowledge/**.md` | chemins valides, cohérence avec les baselines synchronisées | *différé* — evals sur golden set |
| `data/interactive/` | *hors périmètre* — créé par l'usage du produit, jamais par une PR | *hors périmètre* — voir L6 pour la protection dans l'autre sens |
| `config/sources.yaml` | schéma valide, aucun secret en clair | `/selftest` |
| `docs/`, `README` | fichiers et chemins cités existants | — |
| workflows, seuils, hooks | tests du paved road, `codeowners/errors` vide | approbation humaine (`CODEOWNERS`) |

Deux lignes portent la mention *différé* : voir « Chantiers différés ». D'ici là, skills et knowledge ne
sont couverts que par leur preuve déterministe — couverture partielle, assumée et écrite plutôt que
silencieuse.

### Qui merge

Un **pair citizen developer** approuve et merge : une seconde personne non technique regarde les preuves
et les critères, jamais le code. Elle attrape le cas que les gates ne verront jamais — « ça marche, mais
ce n'est pas ce qu'il fallait faire ».

Encore faut-il qu'elle ait de quoi regarder. Une PR présente par défaut un diff qu'elle ne sait pas lire
et des fichiers d'attestation au format machine : rien ne distinguerait alors une approbation instruite
d'un réflexe. **La description de PR est donc générée** à partir des attestations — une ligne par `DOD-N`
avec son verdict en français, le lien vers sa preuve, et ce qui n'a pas été démontré. S'y ajoutent les
signaux qu'une personne non technique peut interroger sans lire le code, au premier rang desquels les
suppressions de tests et les modifications d'assertions existantes : la famille D interdit de désarmer un
test pour se débloquer, mais rien aujourd'hui ne le détecte — modifier une valeur attendue passe le
contrôle de qualité des tests et ne bouge pas la couverture. Ce compte ne bloque pas, il rend visible, et
c'est ce qui donne un contenu à l'approbation.

Comme pour la dette assumée de L0, le durcissement a son déclencheur écrit : **la première fois qu'une PR
approuvée s'avère ne pas faire ce que demandait la DoD**, l'approbation exige de cocher une case par
`DOD-N` plutôt qu'un bouton global.

#### Ce que GitHub permet exactement

La sémantique est plus étroite qu'on ne le suppose, et elle contraint le modèle.

- Il **n'existe pas** de réglage « l'auteur ne peut pas merger sa propre PR ». Aucune option ne le fait.
- Le seul levier est `required_approving_review_count`. Comme GitHub interdit *nativement* — et sans
  réglage possible — d'approuver sa propre PR, exiger une approbation implique mécaniquement qu'une
  seconde personne intervienne. C'est ce qui produit l'effet recherché.
- Une fois l'approbation obtenue d'un tiers, **l'auteur peut lui-même cliquer sur « Merge »**. Interdire
  cela n'est pas faisable nativement, et n'a pas de raison de l'être ici : ce qu'on veut est un regard
  croisé, pas un rituel de délégation.
- `required_approving_review_count: 0` combiné à `require_code_owner_reviews: true` bloque bien le merge :
  les deux réglages s'évaluent séparément, mettre le compteur à zéro retire l'exigence générique et non
  celle des code owners. En revanche une **draft PR ne déclenche pas** la demande d'approbation code owner
  tant qu'elle n'est pas passée « ready for review » — ce qui contraint le durcissement prévu en L0.

#### Prérequis humain, à traiter avant d'armer le réglage

Le dépôt compte aujourd'hui six collaborateurs, tous techniques, et aucun `CODEOWNERS`. GitHub exige un
droit `write` explicite pour qu'une approbation compte. Activer `required_pull_request_reviews` avant que
la paire existe revient donc à exiger une signature que personne n'a le droit de donner : le dépôt
s'arrête. **« Deux citizen developers avec accès write, et un `CODEOWNERS` écrit » est un livrable nommé
du milestone 0**, préalable au réglage. L'ordre de repli, si la paire tarde, est de livrer
`required_status_checks` seul — il n'a aucun prérequis humain et porte l'essentiel du gain.

C'est un coût réel sur l'autonomie solo, accepté en échange d'un regard métier croisé.

## Dépendances externes : aucune ne porte de guardrail

`akria-pipeline` s'appuie sur Minter (binaire externe, DSL de spécification et couverture spec-vers-test)
et GitNexus (index de code en graphe, blast radius).

**Principe retenu : une dépendance externe enrichit, elle ne bloque jamais.** Leur absence rendrait un
gate infranchissable — c'est exactement l'incident P0 vécu par Akria, où `minter-validate` était garanti
rouge sur tout run réel.

- **De Minter, on garde le principe, pas le binaire** : chaque criterion référencé par un test. Réalisable
  sans dépendance ni installation en CI.
- **De GitNexus, on garde l'idée** : mesurer le blast radius plutôt que le déclarer. La version agnostique
  s'appuie sur le graphe d'imports du dépôt. L'outil reste un amplificateur possible, jamais un gate.

## Ce que le paved road retire de l'existant

- **`.claude/rules/zones-critiques.md`** : supprimé ou vidé de sa promesse de relecture humaine. Ses zones
  se répartissent entre `CODEOWNERS` (L2), la façade des tableaux de bord et les règles ruff (L6) —
  répartition à faire ligne à ligne, sans quoi la suppression est une régression déguisée en remplacement.
  Conserver un document qui annonce une relecture que personne n'assurera est un risque en soi.
- **spec-kit** : les neuf commandes `/speckit.*`, `.specify/` et `specs/` sont retirés. Deux parcours de
  spécification concurrents feraient deux sources de vérité. La constitution est dépouillée de ses
  invariants avant suppression — mais l'inventaire doit être fait **ligne à ligne et acté par écrit**,
  parce que certains n'entrent dans aucune des deux cases de la règle de partage : un « modèle de menaces »
  obligatoire par spécification, une revue de sécurité pour tout changement touchant l'authentification ou
  l'accès aux données, ne sont ni des invariants qu'un `grep` vérifie, ni des contraintes propres à une
  demande. Sans arbitrage explicite, la clause de sauvegarde est sincère et vide. Version minimale
  compatible avec la doctrine anti-friction : une question unique dans le gabarit de DoD — « cette demande
  touche-t-elle des données de candidats, une route, un upload, une nouvelle source ? » — dont un « oui »
  active la lentille `security-auditor` **pour cette PR seulement**. Friction nulle sur les demandes
  ordinaires.
- **`CONTRIBUTING.md`** : intégralement construit sur spec-kit, donc orphelin le jour du retrait — et
  c'est la seule porte d'entrée écrite du dépôt. Réécrit en même temps, pas après.
- **`.github/pull_request_template.md`** : checklist d'auteur technique, dont deux items (« le changement
  est minimal et cohérent », « ça ne réinvente pas la roue ») sont la mission de `design-coherence`
  transformée en case à cocher pour quelqu'un qui ne lit pas le code. Remplacé par la description générée
  décrite en « Qui merge ». C'est le même motif que le retrait de spec-kit : deux récits concurrents de ce
  qui a été prouvé.
- **Toute instruction auto-déclarative** (« l'agent DOIT signaler que… ») : convertie en check ou supprimée.
- **`.claude/MAINTENANCE.md`** : les tâches récurrentes sans date de dernière exécution ne sont pas suivies.
  À rattacher au friction log ou à supprimer.

Un retrait dans l'autre sens, qui n'est pas une suppression mais une **levée ciblée** : `.claude/rules/code.md`
interdit à l'agent de commiter et de pousser (« seul l'utilisateur pousse »). Le paved road suppose
exactement le contraire — un journal committé par `advance`, un travail en AFK, un parcours qui s'achève à
l'ouverture de la PR. Sans levée explicite, le citizen developer revient devant une branche locale non
poussée et une console qui lui demande une commande git. La levée est bornée à la branche du paved road,
jamais à `main`, dont la protection porte déjà la garantie.

## Ce qu'on ne fait pas

Explicitement hors périmètre, pour éviter la reprise mécanique d'`akria-pipeline` :

- Neuf stages avec artefacts formels et schémas de validation.
- Frontières à session fraîche, résumés de reprise, ancre de worktree, wrapper de lancement.
- Runtime à compiler, CLI supplémentaire à installer.
- Promotion automatique en production : elle reste la décision de Naël.
- Merge automatique de la PR : un pair citizen developer approuve et merge.

## Plan de mise en œuvre

Chaque milestone est livrable seul et laisse le dépôt cohérent. L'ordre est contraint par les dépendances,
pas par le calendrier.

### Milestone 0 — les gains sans dépendance

Les actions qui n'attendent aucune autre brique et portent le meilleur rapport effort/effet du design.
**L'ordre compte** : chacune des trois premières conditionne la suivante, et les inverser gèle le dépôt.

1. **Remettre `main` au vert** et sortir `pip-audit` du gate bloquant, vers un job `Dependencies` nightly
   non requis. Sans cela, rendre la CI obligatoire enferme tout le monde dehors.
2. **`required_status_checks`** avec `strict: true`, sur les cinq contextes littéraux `Lint & format`,
   `Security`, `Tests`, `Migrations`, `Docker`, vérifiés sur une PR témoin. Plus le contrôle de dérive
   entre la liste requise et les `name:` de `ci.yml`. Aujourd'hui une PR rouge se merge sans obstacle.
3. **Ouvrir le dépôt à deux citizen developers** avec droit `write` explicite, et écrire `CODEOWNERS` sur
   les fichiers de gate. Alors seulement, `required_pull_request_reviews` avec `require_code_owner_reviews`.
4. **Activer les règles ruff gratuites** — `TID252`, `S113`, `E722`, mesurées à zéro violation — puis
   `TID251` configuré. Mettre `S608` et `BLE001` en observation, avec leurs 18 et 8 cas actuels comme
   baseline. Retirer en même temps de `.claude/hooks/check_python.py` les checks que ruff reprend, sinon
   deux implémentations de la même règle divergent.
5. **Poser le check de protection des routes** (voir L5) avec sa baseline gelée : bloquant sur les routes
   neuves, muet sur l'existant.
6. **Rendre l'environnement de développement atteignable** : une cible `setup` idempotente et une cible
   `doctor` dont chaque échec est une phrase française actionnable. Sans elles, le premier run d'une
   personne non technique tombe en famille B — « arrêt immédiat, panne » — c'est-à-dire en break-glass,
   alors que le break-glass est censé être l'exception. Aujourd'hui rien n'existe entre le clone et un
   `.env` de 170 lignes, trois services à lancer et cinq clés d'accès à obtenir.

**Fin :** le dépôt est protégé pour tout le monde, y compris pour le travail qui ne passera jamais par le
paved road, et une personne non technique peut atteindre l'état où le parcours commence.

### Milestone 1 — Instrumentation et friction log

Mesure de durée et de coût par étape, consignation des frictions, mécanisme de ratchet. Remonté en tête
du plan : le design pose qu'« aucune contrainte n'est ajoutée par anticipation », et construire les
niveaux coûteux avant de disposer de l'instrument qui les justifie contredit sa propre doctrine. Le coût
est faible — les données existent déjà en base (`conversations.usage_input_tokens`, `usage_events`,
`pr_url`) — et ce milestone ne dépend d'aucun autre.

Il fournit aussi la ligne de base sans laquelle « le paved road coûte-t-il moins cher que l'existant ? »
restera une opinion, et la donnée de promotion du ratchet est prise là où elle se trouve réellement : les
conclusions des check runs GitHub, la CI ne pouvant pas écrire dans le journal d'une branche.

**Fin :** tout niveau ajouté ensuite l'est avec un chiffre en face.

### Milestone 2 — L0, Definition of Done

Format de `definition-of-done.md` et critères de qualité d'un acceptance criterion observable. Parcours de
validation en français. Emplacement des artefacts et politique de versionnement.
**Fin :** une fonctionnalité réelle traverse le parcours de bout en bout avec Definition of Done validée
et attestations, sans outillage.

### Milestone 3 — L1, Attestation

State journal par branche, commande d'avancement adossée aux codes de sortie, check de fraîcheur des
attestations adossé aux empreintes d'arbre des chemins prouvés. Check de contenu des attestations
(texte structuré uniquement, dépôt public). Cibles `Makefile`. Tests du paved road lui-même.
**Fin :** l'avancement est impossible sans exécution réelle ; une evidence périmée bloque.

### Milestone 4 — L2, Quality Gates

Les réglages GitHub sont faits au milestone 0. Reste : brancher les checks du paved road (DoD présente,
attestations valides pour le contenu prouvé) sur la CI **selon le déclencheur de périmètre**, poser le
`pre-push` rapide, et restituer les échecs en français avec leur famille.

La restitution ne suffit pas côté ligne de commande : la surface où le citizen developer voit un refus est
la boîte de merge GitHub — cinq noms de checks en anglais, une croix rouge, et en cliquant la sortie brute
d'un linter ou d'un outil de couverture. D'où **un check requis supplémentaire, nommé en français** (« Ce
qui devait marcher »), dont le résumé affiche le tableau des `DOD-N` avec démontré / non démontré et la
famille de l'échec. C'est le seul qu'il consulte ; les cinq autres peuvent rester techniques. Coût : un job
qui lit le journal déjà committé.
**Fin :** aucun rouge ne peut atteindre `main`, quel que soit l'agent ; un échec dit ce qu'il faut faire.

### Milestone 5 — L3, E2E

Introduction de Playwright, dans un job CI dédié. Génération d'un test par acceptance criterion. Exécution
en CI sur chaque PR et en nightly, contre l'URL locale **et** celle de la review app. Prérequis à lever
d'abord : le second mode d'entrée par secret sur les review apps.
**Fin :** « ça marche » cesse d'être une affirmation de l'agent et devient une sortie reproductible, qui
protège aussi contre les régressions futures.

### Milestone 6 — L4, Smoke

Parcours exploratoire piloté par MCP, en local puis sur la review app, par le même second mode d'entrée
que L3. Captures destinées au citizen developer, transitant hors dépôt.
**Fin :** ce qu'aucun test n'avait prévu devient visible avant la PR.

### Milestone 7 — L5 puis L6, au fil des frictions

`design-coherence` seule pour ouvrir L5 ; la façade des tableaux de bord pour L6, ancrée à l'écriture et
à l'exécution, une fois les TDB comptés. Les règles ruff et le check de protection des routes sont déjà
posés au milestone 0. Ensuite, une lentille ou une fitness function à la fois, uniquement quand le
friction log la réclame — et le cliquet vers `blocking` ne concerne que les checks déterministes, une
lentille LLM restant en `warning` permanent puisqu'elle ne peut pas vivre dans les Guardrails.
**Fin :** aucune — c'est le régime permanent.

## Risques

| Risque | Conséquence | Traitement |
|---|---|---|
| Acceptance criteria vagues | Toute la chaîne perd son référentiel | Observabilité vérifiée à L0, durcie en fitness function à L6 |
| Le paved road devient du code non maintenu | Les gates rouillent et deviennent inertes | Testé comme le produit, dans la même CI |
| Adoption nulle par excès de friction | Aucune garantie effective | Ratchet, démarrage permissif, périmètre de déclenchement étroit, seuil d'alerte chiffré adossé au milestone 1 |
| Evidence fabriquée par l'agent | Le jugement redevient auto-déclaratif | Fraîcheur vérifiée dès L1, exécution réelle en L3 |
| Changement d'agent | Perte de l'enforcement | Garantie logée dans les Guardrails, indépendants de l'agent |

## Questions ouvertes

- Coût réel d'un parcours complet en durée et en tokens : à mesurer au milestone 1, non à estimer.
- Contenu de la description de PR, maintenant qu'un pair citizen developer en est le lecteur.
- Faisabilité exacte du second mode d'entrée sur les review apps : le buildpack expose toute la
  configuration d'oauth2-proxy par variables d'environnement, reste à valider la production du fichier de
  secrets au démarrage. Conditionne L3 et L4 contre review app — et lève au passage la question de
  `/selftest` derrière oauth2-proxy, si l'annexe est un jour traitée.

Deux questions ouvertes ont été refermées. La sémantique de `required_approving_review_count: 0` combiné à
`require_code_owner_reviews: true` : les deux réglages s'évaluent séparément, la combinaison bloque bien
le merge, mais une draft PR ne déclenche pas la demande d'approbation code owner — voir « Qui merge ». Et
le rattachement des attestations, qui ne passe plus par le SHA de HEAD — voir L1.

## Chantiers différés

Identifiés, non ouverts. Chacun mérite son propre cycle de conception.

**Evals en CI pour les skills et le knowledge.** Un `SKILL.md` est du prompt exécuté en production :
ni lint, ni test, ni E2E n'en disent quoi que ce soit, et une instruction mal rédigée dégrade les réponses
sans que rien ne l'indique. L'outillage existe déjà en partie dans `evals/` (`run_eval.py`, `questions.py`,
`compare.py`, `blind_eval.py`), non branché à la CI ni au `Makefile`.

Ce qu'en dit l'état de l'art : constituer un golden dataset stable de 20 à 50 cas avant de brancher quoi
que ce soit ; démarrer par une dizaine de cas sur le prompt le plus fragile ; privilégier les checks
déterministes et réserver le jugement par modèle au réellement subjectif. Deux familles d'outils —
`promptfoo` (YAML, seuil de réussite en CI) et `DeepEval` (assertions pytest, natif Python, donc plus
proche de ce dépôt) — sans préjuger du choix, l'extension de `evals/` restant l'option la moins coûteuse
en dépendances.

**Régression de coût.** Une instruction plus verbeuse dans un `SKILL.md` se paie sur chaque conversation,
indéfiniment. Mesurer les tokens consommés par une passe d'eval et alerter au-delà d'un écart traiterait
la dérive avant la facture.

Anthropic préconise par ailleurs une méthode *evaluation-first* pour les skills : écrire les évaluations
avant les instructions. À considérer le jour où ce chantier s'ouvre.

## Annexe — hors périmètre

Le paved road est un workflow de développement, du besoin jusqu'à la PR. Ce qui suit relève d'un autre
chantier, indépendant, et n'est consigné ici que pour ne pas être oublié.

**Le déploiement staging n'est pas vérifié.** `_deploy.yml` pousse vers Scalingo et s'arrête : aucun
contrôle de santé, aucun rollback. Un déploiement cassé reste invisible jusqu'à ce qu'un humain ouvre la
page. La brique de diagnostic existe pourtant déjà — la route `/selftest` (`web/selftest.py`) vérifie les
services. Traitement possible : le workflow attend le redémarrage, appelle `/selftest`, échoue bruyamment
sinon.

**La promotion en production se décide sans dossier.** Naël pose un tag `v*.*.*` sans disposer d'un
récapitulatif de ce qui part, de ce qui a été démontré, de ce qui ne l'a pas été, ni de quoi surveiller.
Les attestations produites par le paved road fourniraient la matière d'un tel document, si le besoin se
confirme.

## Références

- [Paved Roads, Golden Paths, Guardrails and Railroads — The New Stack](https://thenewstack.io/paved-roads-golden-paths-guardrails-and-railroads/)
- [Platform engineering control mechanisms — Google Cloud](https://cloud.google.com/blog/products/application-modernization/platform-engineering-control-mechanisms)
- [Fitness Functions — Continuous Architecture](https://continuous-architecture.org/practices/fitness-functions/)
- [SLSA — FAQ et modèle de niveaux](https://slsa.dev/spec/v1.1/faq)
- [in-toto and SLSA — attestations](https://slsa.dev/blog/2023/05/in-toto-and-slsa)
- [Ratchets: improving systems incrementally](https://www.dustyburwell.com/2019/05/29/ratchets)
