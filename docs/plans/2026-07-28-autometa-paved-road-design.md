# Autometa Paved Road — design

Un *paved road* pour citizen developers : un chemin guidé qui rend le bon choix facile, doublé de
guardrails qui s'appliquent quel que soit le chemin emprunté.

Statut : design validé, plan de mise en œuvre à exécuter. Date : 2026-07-28.

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

Objectif : **99 % d'autonomie**, un humain technique en break-glass pour le cas catastrophique.

## Décisions actées

| Sujet | Décision |
|---|---|
| Public | Citizen developers, fonctionnalités applicatives complètes |
| Autonomie | 99 %, break-glass réservé au cas grave |
| Autorité | Attestations, fitness functions, adversarial review, tests-contrat — les quatre |
| Prod | Le paved road s'arrête à la PR ; un pair citizen developer merge ; Naël promeut par tag |
| Durée | Sans contrainte, le travail se fait en AFK |
| Filiation | Déclinaison allégée de `akria-pipeline`, doctrine reprise, volume écarté |
| Trajectoire | Empilement de niveaux, jamais un déploiement en bloc |
| Outillage | Cibles du `Makefile` existant, aucune nouvelle CLI à installer |
| spec-kit | Retiré ; la Definition of Done le remplace, la constitution est récupérée puis redistribuée |

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
│  git hooks (pre-commit, pre-push) · CI GitHub · deploy vérifié     │
│  → c'est ICI que rien ne peut passer.                              │
└────────────────────────────────────────────────────────────────────┘
```

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
  │ L1  ATTESTATION                       │   ●○○○○   plus aucun PASS
  │     state journal, advance, evidence  │           auto-déclaré
  │     plus fraîche que le code          │
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
La forme reste assez régulière pour qu'un check puisse refuser le flou et pour que le parcours de smoke (L3)
s'en dérive.

Règles associées :

- **Identifiants stables** (`DOD-1`, `DOD-2`…), jamais réutilisés. Ils portent le pont vers les tests (L3)
  et le référencement dans les attestations.
- **Fichier committé**, attaché à la PR. Chez Akria les artefacts de run sont gitignorés — cohérent
  puisque l'enforcement y vit dans les hooks locaux ; ici il vit dans la CI, qui ne voit pas un fichier ignoré.
- **Pas de borne dure sur le nombre**, mais un signal en `warning` : un ou deux critères pour une
  fonctionnalité applicative laisse soupçonner du vague, au-delà d'une quinzaine la demande devrait être
  découpée.
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
| **Self-grill contre la source de vérité** | Les critères se dérivent des sources sélectionnées par les règles ci-dessous. Ce qu'une lecture peut trancher devient une assertion réfutable, pas une question posée |
| **Questions ouvertes vides** | Un check refuse de sceller L0 si des ambiguïtés subsistent : le « quoi » se fixe ici et nulle part ailleurs |
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

Quatre verbes suffisent — démarrer, consulter l'état, lancer les checks, avancer — exposés comme cibles
du `Makefile` existant, donc invocables par n'importe quel agent, par la CI, ou à la main.

#### Rattachement au code : le SHA, pas la date

Akria compare des dates de fichiers (`smoke-evidence` : les captures doivent être plus récentes que
`verify-report.yaml`). Insuffisant ici : l'agent dispose de Bash, et `touch` rend n'importe quelle capture
« fraîche ». Une date de fichier n'est pas une attestation, c'est une affirmation horodatée.

**Chaque attestation enregistre le SHA de HEAD au moment de sa production.** Un check refuse si HEAD a
bougé depuis. Conséquence assumée : tout nouveau commit invalide les attestations et impose de re-prouver
— acceptable puisque le travail se fait en AFK. Bénéfice : l'attestation devient vérifiable par quiconque,
CI comprise, sans faire confiance à l'horloge ni au système de fichiers.

#### Granularité : une attestation par critère

Chaque `DOD-N` porte la sienne : ce qui a été fait, ce qui a été observé, la preuve jointe, le SHA, et un
verdict démontré / non démontré. Un critère non démontré ne peut donc pas se noyer dans un rapport global.
Le récapitulatif en français n'est pas dupliqué ici : il est produit par le release brief (L3) à partir de
ces attestations.

#### États et journal

Trois états, alignés sur les trois temps du parcours : `align`, `build`, `prove`. Le journal est **committé**
— la CI porte les guardrails et ne verrait pas un fichier ignoré. Seul `advance` y écrit, et seulement
d'après des codes de sortie réels.

#### Échecs : tri par famille, pas compteur

Akria force une pause au troisième échec consécutif. Un compteur brut est un mauvais outil, parce que les
échecs n'appellent pas la même réponse :

| Famille | Causes | Réponse |
|---|---|---|
| **A. Réparable** | test rouge, lint, couverture sous le seuil, attestation invalidée par un commit, rebase à faire | L'agent réessaie — c'est le travail normal |
| **B. Environnement** | Postgres ou Redis absent, Matomo ou Metabase indisponible, réseau | Arrêt immédiat, signalé comme panne. Réessayer brûle du temps sans rien corriger |
| **C. Question métier** | critère ambigu, critère infaisable découvert tard, périmètre flou | Retour au citizen developer — HITL checkpoint |
| **D. Interdit** | tentative d'abaisser un seuil, migration destructive, suppression de test | Break-glass |

Réessayer sur A est légitime et fréquent ; réessayer sur B, C ou D est une erreur dès la première fois.
Chaque check déclare donc sa famille, et c'est elle qui commande la suite — pas un seuil.

### L2 — Quality Gates

Ce niveau protège **tout le monde** — paved road ou pas, Claude ou Codex, humain ou cron.

#### Le trou principal n'est pas dans la CI, il est dans son branchement

`main` est protégée : force-push interdit, historique linéaire, suppressions bloquées, admins inclus, push
direct fermé. Mais l'API ne renvoie **ni `required_status_checks`, ni `required_pull_request_reviews`**.

Conséquence : la CI est complète et rien n'oblige qu'elle soit verte pour merger. Une PR rouge se merge
aujourd'hui sans obstacle. Le premier geste de L2 n'est donc pas du développement mais deux réglages GitHub,
à coût nul et à effet immédiat sur tout le dépôt :

- **`required_status_checks`** sur les cinq jobs existants — `lint`, `security`, `test`, `migrations`,
  `docker`.
- **`required_pull_request_reviews`** avec `require_code_owner_reviews`, sans quoi le `CODEOWNERS`
  ci-dessous reste décoratif.

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
maintenir. Il réintroduit une relecture humaine, mais sur un périmètre minuscule et immuable : c'est
précisément le break-glass, et il ne se déclenche jamais sur du travail applicatif ordinaire.

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

**Exécution : CI sur chaque PR, plus une passe nightly.** Le test est écrit pour tourner indifféremment
contre une URL locale ou une URL de review app. Point d'attention : le `up`/`down` des review apps sera
migré dans la CI — ne pas construire de mécanisme local qui serait jeté.

Rien de tel n'existe aujourd'hui dans le dépôt : Playwright est à introduire. C'est le seul vrai chantier
technique de ce niveau.

### L4 — Smoke

Le pendant exploratoire de L3, et son complément exact : là où l'E2E vérifie ce qui était prévu, le smoke
attrape **ce que personne n'avait pensé à tester** — le bouton présent mais illisible, la page qui rame,
le PDF techniquement conforme et visuellement raté.

Piloté via MCP, en local puis sur la review app. Non déterministe, non rejouable, dans les Adapters — et
ici ce n'est pas un défaut : on ne lui demande pas de garantir, on lui demande de regarder. Son adaptabilité
est précisément ce que la rigidité d'un test ne sait pas faire.

| | Public | Produit | Rôle |
|---|---|---|---|
| **E2E** (L3) | la machine | un verdict rouge ou vert | bloque, et défend dans la durée |
| **Smoke** (L4) | le citizen developer | des captures, un parcours réel | montre, et découvre l'imprévu |

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
| `auth-audit` | Route FastAPI sans protection. `.claude/rules/review.md` le liste en critère de rejet sans rien pour le détecter | Équivalent de `decorator-audit` (Nest) |
| `dod-test-fidelity` | Un test marqué `DOD-N` est bien un parcours réel, pas un test unitaire déguisé | Équivalent de `tag-fidelity` (minter) |
| `query-cost` | Segments Matomo à 30-180 s, jamais plus de 5 requêtes segmentées en boucle — un agent tombe dedans naturellement | Propre au dépôt |
| `knowledge-drift` | `knowledge/` diverge du code ; `MAINTENANCE.md` le liste comme tâche trimestrielle jamais faite | Propre au dépôt |

Deux besoins souvent cités — conformité aux `.claude/rules/` et sûreté des migrations — n'apparaissent pas
ici : ils sont largement automatisables et relèvent donc de L6. Une lentille LLM qui vérifie ce qu'un `grep`
fait mieux est du gaspillage.

### L6 — Fitness Functions

Terme de Neal Ford (*Building Evolutionary Architectures*) : une règle exécutable qui mesure qu'un système
préserve les propriétés voulues à mesure qu'il change. Chaque règle de `.claude/rules/` qui compte
réellement en devient une. Deux chantiers structurants :

#### D'abord ce qui est déjà écrit ailleurs

La configuration ruff active déjà `E`, `F`, `W`, `I`, `G` — l'interdiction des f-strings dans les logs est
donc **déjà appliquée**. Mais quatre règles rédigées en prose dans `.claude/rules/` correspondent à des
règles ruff simplement pas activées :

| Règle en prose | Règle ruff |
|---|---|
| Imports relatifs parents interdits | `TID252` |
| `httpx` exclusivement — jamais `requests`, `urllib`, `unittest`, `psycopg2` | `TID251` |
| Tout appel HTTP a un timeout explicite | `S113` |
| `os.getenv` uniquement dans `web/config.py` | `TID251` + `per-file-ignores` |

Quatre règles déclaratives devenues bloquantes pour une dizaine de lignes de `pyproject.toml`, dans une CI
déjà branchée et déjà rendue obligatoire par L2. C'est le meilleur rapport effort/effet du design, et c'est
par là que L6 commence — en mesurant d'abord ce que ça fait remonter sur le code existant.

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
autorisé, avec un check qui interdit tout autre import depuis `data/interactive/`. On cesse de courir après
les cassures : on réduit la surface où elles peuvent se produire. La façade devient un contrat, ses tests
en sont la preuve, et modifier ce contrat devient un acte visible plutôt qu'un effet de bord.

Trois conséquences à traiter :

- Migrer les TDB existants vers la façade.
- `data/` est aujourd'hui exclu de ruff (`exclude = ["data/", …]`) : le check d'import demande soit de
  lever l'exclusion pour ce seul contrôle, soit un check maison.
- `.claude/rules/code.md` prescrit actuellement aux apps interactives d'utiliser `lib.query`, `web.db` et
  `web.config` directement. Cette règle est à réécrire en même temps, sinon elle contredit la façade.

C'est ce qui remplace réellement `zones-critiques.md` : non pas une liste de fichiers assortie d'une
promesse de relecture que personne n'honorera, mais une frontière que le code ne peut pas franchir.

#### Le pont critère → test est déjà acquis

Prévu ici à l'origine, il est obtenu gratuitement en L3 : Playwright génère un test par `DOD-N`. Il ne
reste qu'à vérifier la correspondance, ce que fait la lentille `dod-test-fidelity`.

#### En réserve

SQL interpolé, migrations destructives, dérive `knowledge/` — écrits quand le friction log les réclame.

## Mécanismes transversaux

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

**La décision de passage est humaine, prise sur données.** Le journal committé enregistre déjà chaque
échec de gate avec sa famille : il fournit gratuitement, pour chaque check en observation, le nombre de
déclenchements et leur nature. Le jugement reste là où il a de la valeur ; il ne s'exerce pas à vide.

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
| **Break-glass escalation** | l'agent ne peut pas garantir sans décision d'ingénierie | personne dans la boucle — c'est le 1 % |

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

| Artefact modifié | Preuve déterministe | Preuve comportementale |
|---|---|---|
| `web/`, `lib/` | lint, tests, couverture 90 % du diff, migrations | E2E Playwright, un test par `DOD-N` |
| `skills/*/SKILL.md` | frontmatter valide, chemins et scripts cités existants | *différé* — evals sur golden set |
| `knowledge/**.md` | chemins valides, cohérence avec les baselines synchronisées | *différé* — evals sur golden set |
| `data/interactive/` | imports via la façade uniquement | exécution réelle du `cron.py` |
| `config/sources.yaml` | schéma valide, aucun secret en clair | `/selftest` |
| `docs/`, `README` | fichiers et chemins cités existants | — |
| workflows, seuils, hooks | tests du paved road | CODEOWNERS |

Deux lignes portent la mention *différé* : voir « Chantiers différés ». D'ici là, skills et knowledge ne
sont couverts que par leur preuve déterministe — couverture partielle, assumée et écrite plutôt que
silencieuse.

### Qui merge

Un **pair citizen developer** approuve et merge : une seconde personne non technique regarde les preuves
et les critères, jamais le code. Elle attrape le cas que les gates ne verront jamais — « ça marche, mais
ce n'est pas ce qu'il fallait faire ».

Contrainte GitHub à connaître : un auteur ne peut pas approuver sa propre PR. Exiger une approbation
implique donc structurellement d'être deux. C'est un coût réel sur l'autonomie solo, accepté en échange
d'un regard métier croisé.

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

- **`.claude/rules/zones-critiques.md`** : supprimé ou vidé de sa promesse de relecture humaine, remplacé
  en L6 par la façade des tableaux de bord et les règles ruff. Conserver un document qui annonce une
  relecture que personne n'assurera est un risque en soi.
- **spec-kit** : les neuf commandes `/speckit.*`, `.specify/` et `specs/` sont retirés. La constitution est
  dépouillée de ses invariants — permanents en guardrails, spécifiques en acceptance criteria — avant
  suppression. Deux parcours de spécification concurrents feraient deux sources de vérité.
- **Toute instruction auto-déclarative** (« l'agent DOIT signaler que… ») : convertie en check ou supprimée.
- **`.claude/MAINTENANCE.md`** : les tâches récurrentes sans date de dernière exécution ne sont pas suivies.
  À rattacher au friction log ou à supprimer.

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

Deux actions qui n'attendent aucune autre brique et portent le meilleur rapport effort/effet du design.

- **Rendre la CI obligatoire au merge** : `required_status_checks` sur les cinq jobs,
  `required_pull_request_reviews` avec `require_code_owner_reviews`, `CODEOWNERS` sur les fichiers de gate.
  Aujourd'hui une PR rouge se merge sans obstacle.
- **Activer les quatre règles ruff** (`TID251`, `TID252`, `S113`, per-file-ignores) et mesurer ce qu'elles
  font remonter sur le code existant.

**Fin :** le dépôt est protégé pour tout le monde, y compris pour le travail qui ne passera jamais par le
paved road.

### Milestone 1 — L0, Definition of Done

Format de `definition-of-done.md` et critères de qualité d'un acceptance criterion observable. Parcours de
validation en français. Emplacement des artefacts et politique de versionnement.
**Fin :** une fonctionnalité réelle traverse le parcours de bout en bout avec Definition of Done validée
et attestations, sans outillage.

### Milestone 2 — L1, Attestation

State journal par branche, commande d'avancement adossée aux codes de sortie, check de fraîcheur des
attestations. Cibles `Makefile`. Tests du paved road lui-même.
**Fin :** l'avancement est impossible sans exécution réelle ; une evidence périmée bloque.

### Milestone 3 — L2, Quality Gates

Les réglages GitHub sont faits au milestone 0. Reste : brancher les checks du paved road (DoD présente,
attestations valides pour le SHA) sur la CI, poser le `pre-push` rapide, et restituer les échecs en
français avec leur famille.
**Fin :** aucun rouge ne peut atteindre `main`, quel que soit l'agent ; un échec dit ce qu'il faut faire.

### Milestone 4 — L3, E2E

Introduction de Playwright. Génération d'un test par acceptance criterion. Exécution en CI sur chaque PR
et en nightly, contre une URL locale ou de review app. Attestations rattachées au SHA.
**Fin :** « ça marche » cesse d'être une affirmation de l'agent et devient une sortie reproductible, qui
protège aussi contre les régressions futures.

### Milestone 5 — L4, Smoke

Parcours exploratoire piloté par MCP, en local puis sur la review app. Captures destinées au citizen
developer.
**Fin :** ce qu'aucun test n'avait prévu devient visible avant la PR.

### Milestone 6 — Instrumentation et friction log

Mesure de durée et de coût par étape, consignation des frictions, mécanisme de ratchet.
**Fin :** les niveaux suivants sont pilotés par des incidents constatés, non par des hypothèses.

### Milestone 7 — L5 puis L6, au fil des frictions

`design-coherence` seule pour ouvrir L5 ; les quatre règles ruff et le check `data/interactive/` pour L6.
Ensuite, une lentille ou une fitness function à la fois, en `warning` puis en `blocking`, uniquement quand
le friction log la réclame.
**Fin :** aucune — c'est le régime permanent.

## Risques

| Risque | Conséquence | Traitement |
|---|---|---|
| Acceptance criteria vagues | Toute la chaîne perd son référentiel | Observabilité vérifiée à L0, durcie en fitness function à L5 |
| Le paved road devient du code non maintenu | Les gates rouillent et deviennent inertes | Testé comme le produit, dans la même CI |
| Adoption nulle par excès de friction | Aucune garantie effective | Ratchet, démarrage permissif, fast path |
| Evidence fabriquée par l'agent | Le jugement redevient auto-déclaratif | Fraîcheur vérifiée dès L1, exécution réelle en L3 |
| Changement d'agent | Perte de l'enforcement | Garantie logée dans les Guardrails, indépendants de l'agent |

## Questions ouvertes

- Coût réel d'un parcours complet en durée et en tokens : à mesurer au milestone 6, non à estimer.
- Comportement exact de `required_approving_review_count: 0` combiné à `require_code_owner_reviews: true`
  sur GitHub : à confirmer à l'implémentation, la sémantique est subtile.
- Contenu de la description de PR, maintenant qu'un pair citizen developer en est le lecteur.
- Ce que devient `/selftest` derrière oauth2-proxy si l'annexe est un jour traitée.

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
