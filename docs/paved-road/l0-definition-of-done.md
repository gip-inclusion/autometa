# L0 — Definition of Done

Ce document fixe le format de `definition-of-done.md`, les règles qui le gouvernent et le parcours
de validation. Il ne décrit aucun outillage : à ce stade, L0 se tient à la main.

Origine et justifications : `docs/plans/2026-08-22-paved-road-workflow.md`, section « L0 —
Definition of Done ».

## Ce que L0 garantit, et ce qu'il ne garantit pas

La garantie de L0 est **humaine** : la validation du citizen developer, et rien d'autre. Les
lentilles adversariales qui préparent le contrat réduisent la probabilité qu'il soit complaisant,
elles ne l'interdisent pas — un agent qui rédige ses propres critères d'acceptation reste juge et
partie tant que personne d'autre n'a lu le résultat.

Ce qu'un exécutable saura constater plus tard est court, et c'est tout ce qu'on lui demandera :

- le fichier existe à l'emplacement attendu ;
- le format `DOD-N` est respecté ;
- les identifiants sont uniques ;
- aucun placeholder de gabarit (`<…>`) n'a survécu à la rédaction ;
- les sections « Questions ouvertes » et « Validation » sont présentes.

« Un check refuse de sceller L0 s'il subsiste des ambiguïtés » ne veut rien dire côté machine : un
programme constate une section vide, pas une absence d'ambiguïté, et une section se vide en une
ligne. Aucun contrôle automatique ne remplace la lecture.

## Emplacement et versionnement

Deux artefacts par fonctionnalité, sous un répertoire unique nommé d'après la branche, préfixe
retiré :

```
paved-road/<slug>/
  definition-of-done.md
  attestations/
```

`docs/paved-road/` porte la spécification du parcours ; `paved-road/` porte les artefacts produits
par un parcours réel. Les deux ne se mélangent pas.

Le fichier est **committé et attaché à la PR**. L'enforcement vit ici dans la CI, qui ne voit pas un
fichier gitignoré. Le répertoire est conservé après le merge : il est la trace de ce qui avait été
convenu, et les attestations s'y rattachent.

## Format

Le fichier est écrit en français, lu par une personne non technique, et tient sur un écran.

```markdown
# <Titre de la fonctionnalité>

## Ce que je veux

<Deux ou trois phrases. L'intention, pas la solution.>

## Ce qui devra marcher

DOD-1 — <Résultat observable, au présent, du point de vue de la personne qui s'en sert.>

DOD-2 — <…>

## Sources lues

<Chaque source, avec la règle qui l'a déclenchée. Voir « Règles de sélection des sources ».>

## Questions ouvertes

<Ce qu'aucune lecture n'a tranché, ou « Aucune ».>

## Validation

Validé par <nom> le <AAAA-MM-JJ>.
```

Exemple canonique :

```markdown
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

Le contexte n'apparaît que lorsqu'il compte — ici sur `DOD-3` seulement. Gherkin complet a été
écarté : quatre critères y occupent une page, et la cérémonie fatigue précisément le lecteur qui
doit lire ce fichier. La forme reste assez régulière pour qu'un contrôle refuse le flou et pour que
le parcours de smoke (L4) s'en dérive.

### Identifiants

`DOD-1`, `DOD-2`… **stables et jamais réutilisés**, y compris après le retrait d'un critère : un
identifiant retiré laisse un trou dans la numérotation. Ils portent le pont vers les tests (L3) et
le référencement dans les attestations ; un identifiant recyclé fait pointer une preuve ancienne sur
un critère nouveau.

### Bornes

Une seule borne dure : **au plus cinq critères démontrés par un test de bout en bout**. Au-delà, la
preuve retombe sur une forme déterministe moins coûteuse ou sur le smoke. Sans cette borne, le coût
récurrent de L3 devient une fonction non contrôlée de la verbosité de la demande.

Le nombre total de critères n'est pas borné, mais deux signaux en `warning` :

- un ou deux critères pour une fonctionnalité applicative laissent soupçonner du vague ;
- au-delà d'une quinzaine, la demande devrait être découpée.

### Immuabilité après validation

Une DoD validée ne se réécrit pas. Un critère qui se révèle infaisable est un **blocage métier** :
retour au citizen developer, jamais une correction silencieuse. Toute modification crée une révision
datée et motivée, ajoutée sous le critère concerné, et redemande validation.

```markdown
DOD-3 — Sur un rapport de 10 000 lignes, le téléchargement aboutit
  en moins de 30 secondes.
  Révision 2026-08-14 — seuil porté à 60 s : le rapport le plus lourd
  en base fait 12 400 lignes et le rendu prend 41 s. Revalidé le 2026-08-14.
```

C'est cette règle qui empêche l'agent de rétrécir la cible pour atteindre le vert.

## « Observable » ne veut pas dire « Playwright »

Un critère observable décrit un résultat constatable de l'extérieur. Il ne dit rien de l'outil qui
le constatera, et rien n'oblige cet outil à être un navigateur.

L'exemple canonique le montre à lui seul :

| Critère | Ce qu'il demande | Forme de preuve |
|---|---|---|
| `DOD-1` | un clic déclenche un téléchargement | navigateur — le cas le plus courant, pas le seul |
| `DOD-2` | le contenu d'un fichier produit | assertion sur l'artefact : Playwright pilote un navigateur, il ne lit pas l'intérieur d'un PDF |
| `DOD-3` | une volumétrie et un temps | mesure en nightly, hors du chemin bloquant — instable sur un runner partagé |
| `DOD-4` | un message et l'absence de fichier | navigateur, ou assertion sur la réponse |

Sans cette règle, le parcours réel devient : le citizen developer valide, part, et revient à
« `DOD-3` n'est pas démontrable, acceptez-vous de le retirer ? » — une question technique déguisée
en question métier, exactement ce que le parcours interdit.

### Si un critère se révèle malgré tout indémontrable

La remontée a une forme obligatoire : **au moins deux options, formulées en résultats observables,
avec ce que le citizen developer perd dans chaque cas.**

> `DOD-3` demande une mesure de temps sur un rapport de 10 000 lignes. Deux façons de la tenir :
> — la mesurer chaque nuit sur le plus gros rapport réel : vous saurez le lendemain si l'export a
>   ralenti, pas avant le merge ;
> — la remplacer par « l'export du plus gros rapport aboutit sans erreur », vérifié à chaque
>   changement : vous saurez tout de suite s'il casse, jamais s'il devient lent.

Si l'agent ne sait pas produire deux options ainsi formulées, ce n'est pas un point de décision
métier, c'est un break-glass : le travail s'arrête et la question remonte comme une panne.

## Règle de partage avec les guardrails

> **Invariant permanent → guardrail, jamais dans la DoD. Contrainte propre à la demande →
> acceptance criterion.**

« Le SQL est paramétré », « tout appel HTTP a un timeout », « une migration accompagne tout
changement de modèle » sont vrais pour toutes les demandes : les recopier dans chaque DoD noierait
sous du bruit incompréhensible les trois lignes qui comptent, et le lecteur cesserait de les lire.
Ces règles vivent dans `.claude/rules/`, dans `gates.toml` et dans la CI, où elles protègent aussi
le travail qui ne passe pas par le paved road.

« L'export tient jusqu'à 10 000 lignes », « aucune donnée nominative dans le fichier produit » sont
propres à cette demande : hors du contrat, personne ne les vérifiera.

Le test pratique : *cette phrase serait-elle vraie de la prochaine demande, quelle qu'elle soit ?*
Si oui, elle n'a rien à faire dans la DoD.

## Règles de sélection des sources

Pas de liste fixe de documents à lire : la demande détermine les sources. L'agent décide seul, mais
sa décision est traçable — chaque source lue s'explique par une règle déclenchée, et la DoD dit
lesquelles.

Distinction préalable, souvent confondue : les **sources de données métier** (Zendesk, Metabase,
RPE, Matomo) servent à répondre à une question d'analyse, **jamais** à spécifier une fonctionnalité
d'Autometa. Les tickets Zendesk parlent des Emplois de l'Inclusion, pas de ce logiciel.

| Règle | Déclencheur | Ce qu'elle évite |
|---|---|---|
| **R1** | Toujours : le code existant de la surface nommée | Spécifier ce qui existe déjà à moitié, et produire une preuve verte sans avoir rien fait |
| **R2** | Un critère porte un chiffre → citer sa source de mesure | « 10 000 lignes en 30 s » alors qu'aucun rapport ne dépasse 500 lignes. Un nombre sans provenance est une invention, et il contamine jusqu'à la preuve censée le démontrer |
| **R3** | La demande emploie un terme du glossaire (pass, prescripteur, activation, adoption…) → `knowledge/bizdev/glossaire.md` | Réutiliser un mot métier avec le mauvais sens |
| **R4** | La surface est importée par `data/interactive/` (`lib.query`, `web.db`, `web.config`) → lister les tableaux de bord concernés | Casser des tableaux de bord en production sans le savoir |
| **R5** | Le sujet apparaît dans `docs/plans/` → lire la décision passée | Re-trancher une question déjà tranchée, dans l'autre sens |
| **R6** | La demande porte sur l'usage réel du produit → conversations Autometa en base | Concevoir pour un usage supposé |

**R1 et R2 sont inconditionnelles**, et ce sont elles qui portent le bénéfice : le pire gaspillage
est de construire ce qui existe déjà, et un critère chiffré inventé fausse tout l'aval.

## Parcours de validation

C'est le seul moment où l'on sollicite le citizen developer pendant la conception. La machine lui
restitue en français ce qu'elle a compris et ce qui sera vrai à la fin ; il valide ou corrige. Tout
le reste se déroule sans lui.

**Au plus cinq décisions**, et la forme est contrainte :

- chaque décision a un **défaut déjà choisi** et sa **conséquence observable** en français ;
- **validation par exception** : ne rien dire, c'est accepter le défaut ;
- ce que la lentille `gap-hunter` trouve au-delà de cinq devient un `DOD-N` **proposé avec sa valeur
  par défaut**, pas une question posée ;
- aucune question dont la réponse ne change rien d'observable pour lui ne remonte : si elle ne
  modifie aucun critère, elle relève du défaut technique, que l'agent tranche seul.

> **Décision 2 — Nom du fichier téléchargé.**
> Par défaut : le titre du rapport, par exemple `bilan-mensuel-des-candidatures.md`.
> Autrement : `rapport-42.md`, plus court mais impossible à reconnaître dans un dossier de
> téléchargements.

Sans cette contrainte, la session unique devient un questionnaire de vingt items — la forme
classique de la non-adoption. « Que doit-il se passer si deux personnes exportent le même rapport en
même temps ? » est une question de concurrence : elle ne remonte pas.

La validation est consignée dans la section « Validation » du fichier, avec un nom et une date.

## Antériorité

**Le premier commit de la branche est celui qui ajoute `definition-of-done.md`.**

« Un accord écrit avant de coder » n'est prouvé par aucun autre mécanisme : DoD et code arrivent
dans la même PR, et l'attestation démontre la correspondance au contenu, jamais l'ordre. Sans cette
règle, rien ne distingue un contrat convenu d'avance d'une DoD rédigée après coup pour coller au
code déjà produit — c'est-à-dire le retour exact du « juge et partie » que L0 supprime.

La règle est vérifiable pour un coût nul (`git log --diff-filter=A`). Le contrôle exécutable est du
ressort du milestone 3 ; la règle, elle, s'applique dès maintenant.

## Dette assumée

La validation du citizen developer n'est pas matérialisée par une preuve infalsifiable : une mention
dans le fichier suffit, et l'agent pourrait l'écrire lui-même. C'est le seul point de L0 qui reste
auto-déclaratif, et c'est un choix délibéré contre la friction initiale.

Déclencheur de durcissement : la première fois qu'une DoD apparaît validée sans que le citizen
developer se souvienne de l'avoir lue, la validation passe par une draft PR ouverte dès L0, où
l'approbation GitHub fournit une trace horodatée, attribuée et hors de portée de l'agent.
