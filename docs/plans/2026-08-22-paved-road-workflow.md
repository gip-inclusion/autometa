# Paved road — conception du workflow de développement, étape par étape

Version du 22 août 2026, complétée le 27 août des décisions prises et des corrections déjà
portées au code (voir « Décisions et corrections du 27 août », en fin de document). Ce document
fige un état daté : il n'est pas maintenu au fil de l'eau, il enregistre ce qui a été décidé et
pourquoi. Ce document refond le parcours par lequel une personne qui ne lit pas le code (PM, designer) fait construire une fonctionnalité par un agent jusqu'à une PR qu'elle peut juger. À chaque étape, il distingue ce que l'agent est censé faire (règles non déterministes : skills, rules, lentilles) et ce qui le rattrape quand il ne le fait pas (vérificateurs déterministes : hooks, scripts, CI, réglages GitHub). Il propose trois paliers de mise en place pour démarrer vite.

Ce qui est écrit « existe » a été vérifié le 22 août, dans le dépôt (sommet de la pile `paved-road/09-lenses`, et `main` à `356a5c0`) ou dans les réglages GitHub lus par l'API. Ce qui reste à construire est marqué comme tel. Les durées ont été mesurées sur un poste (12 cœurs).

Un fait nouveau conditionne tout le reste : **`main` a bougé depuis le 12 août**, trois PR fusionnées (#191 : review apps Scalingo pilotées par la CI ; #185 ; #181 le 20 août : suite unitaire hermétique et découpe de la CI en trois jobs de tests). La pile de neuf branches repose sur le `main` du 12 août ; la CI, le `Makefile` et la règle `tests.md` y diffèrent. Plusieurs faits du brief du 19 août sont périmés, ils sont corrigés ici.

### Petit lexique, pour lire la suite sans le code

- **PR** (pull request) : la proposition de changement affichée par GitHub, avec ses vérifications automatiques et son bouton « approuver ». C'est ce que le pair lit.
- **CI** : les vérifications que GitHub lance tout seul sur chaque PR. Rouge sur une vérification requise = pas de fusion ; quelques vérifications informatives (E2E) peuvent être rouges sans bloquer.
- **Contrat**, ou DoD (`definition-of-done.md`, « definition of done ») : le texte en français qui dit ce qui devra marcher, critère par critère (`DOD-1`, `DOD-2`…).
- **Commit** : un enregistrement daté et signé d'un état du code. **Diff** : la liste exacte des lignes changées. Le pair ne lit ni l'un ni l'autre.
- **Break-glass** : un humain technique lève une règle pour une PR, et la dispense est écrite dans le résumé du check.
- **Preuve** (attestation) : pour un critère, une commande lancée, son résultat, le verdict « démontré / non démontré / périmé ».
- **Lentille** : une relecture faite par un modèle avec une question précise. Elle bloque l'agent en session (il corrige avant d'avancer), mais son verdict ne devient jamais un check qui se rejoue en CI.
- **Smoke** : l'agent ouvre l'application dans un navigateur, suit le parcours, prend des captures.
- **Pair** : une seconde personne non technique de l'équipe, qui approuve la PR.
- **Review app** : une copie de l'application déployée pour chaque PR, avec son URL dans l'encart de déploiement de la PR, une fois la CI verte. Elle part d'une base vide : pour une fonctionnalité de tableau de bord ou de données, il n'y aura rien à cliquer. Existe sur `main` (PR #191).
- **Hook** : un petit programme qui tourne automatiquement dans la session de l'agent (avant une écriture, à la fin d'un tour).

---

## 1. Le parcours en une page

```
  demandeur           agent                                              pair
  ─────────           ─────                                              ────
  brief en FR  ──▶  ALIGN  ──▶  BUILD  ──▶  REVIEW  ──▶  PROVE  ──▶  PR  ──▶  main
                    (cadrer)    (coder)     (relire)     (prouver)    description
                    contrat     code        lentille     une preuve   en français
                    DOD-1..N    + tests     + smoke      par critère  + review app
       ◀── ≤ 5 décisions,                                                 ◀── approuve
           réponse recommandée                                               ou refuse
```

Trois états de journal, inchangés : `align`, `build`, `prove`. Un état n'existe que là où une transition se vérifie par un code de sortie ; Review et PR n'en ont pas. Review se joue dans l'état `build`, juste avant la transition vers `prove`.

Le demandeur intervient à trois moments prévus, toujours en français, jamais sur du code :

| Moment | Ce qu'il reçoit | Ce qu'il fait | Comment |
|---|---|---|---|
| Début | un poste préparé une fois à la mise en place (dépôt cloné, `make setup`, Docker, `.env`, Claude Code, extension Chrome, `gh` authentifié) | lance `make claude`, tape `/paved-road:paved-road`, écrit ce qu'il veut en deux ou trois phrases | dans la session |
| Fin d'Align | les deux sections du contrat qui le concernent (« Ce que je veux », « Ce qui devra marcher ») et au plus cinq décisions, chacune avec une réponse recommandée et sa conséquence | répond en une fois ; toute décision qu'il ne conteste pas garde sa réponse recommandée | dans la session |
| PR | une description : un critère par ligne avec son verdict, la review app pour essayer lui-même (l'URL apparaît une fois la CI verte), les captures du smoke s'il y en a eu, ce qui n'a pas été démontré | relit, essaie ; s'il refuse, il écrit dans la PR ce qui ne va pas, puis relance `/paved-road:paved-road`, qui lit ce commentaire et rejoue Build et Review ; les preuves périmées forcent la re-preuve. L'approbation, elle, est le geste du pair (il ne peut pas approuver sa propre PR) | commentaire et bouton GitHub |

Trois arrêts possibles, et seulement trois : une **question métier** (l'agent s'arrête et propose au moins deux options en résultats observables, avec ce que le demandeur perd dans chaque cas) ; une **panne d'environnement** (base, service injoignable) ; un **blocage interdit** (baisser un seuil, supprimer un test — l'agent s'arrête et le dit). Il n'y a pas de technicien référent : l'équipe est entièrement non technique. Sur une panne, c'est l'agent qui diagnostique et se répare quand il peut (voir §9, famille B) ; s'il faut un geste humain, il le dit au demandeur en une phrase concrète (« ouvre Docker Desktop et relance »). Sur un interdit, le `break-glass` suppose d'aller chercher quelqu'un de technique pour l'occasion — c'est rare, et jamais un rôle permanent.

Entre ces moments, l'agent travaille seul. Au premier palier, une session par étape : quand une étape est franchie, l'agent le dit et demande d'ouvrir une nouvelle session et de relancer `/paved-road:paved-road` : une commande, pas une décision. L'enchaînement automatique des étapes est un chantier de palier 3, conditionné au coût.

---

## 2. Principes qui tiennent tout le reste

1. **Attente écrite avant, comparaison après.** C'est le même geste à chaque étape ; seuls changent ce qu'on attend (convention, contrat, test, liste de checks) et qui compare (programme, modèle, GitHub).
2. **Une règle est une paire : instruction + vérificateur.** Une instruction seule est un conseil. Chaque règle déclare où elle est vérifiée : hook, script, job CI, réglage GitHub, ou « nulle part, c'est écrit ». Ce qui n'est vérifié nulle part reste une intention, et on le dit.
3. **La garantie vit hors de l'agent.** Les hooks ne tournent que sous Claude Code et l'agent peut en théorie les éditer. Ce qui garantit, c'est ce qui tourne en CI et ce que GitHub exige avant merge. Les hooks font arriver le refus plus tôt.
4. **Une lentille bloque en session, jamais comme check CI qui rejoue.** Il faut distinguer deux sens de « bloquant ». En session : la lentille tourne après Build, l'agent corrige ses bloqueurs et ne peut pas avancer vers Prove tant qu'il en reste — c'est une boucle de fix, comme chez akria, Pocock et Superpowers, et c'est ce qui empêche de shipper du code qui ne tient pas. En CI : le verdict d'un modèle n'est pas reproductible (le même code peut passer puis échouer au re-run), donc on ne rejoue jamais la lentille dans un check requis, qui clignoterait ; la CI vérifie seulement que le rapport existe et couvre le code final (empreintes d'arbre), et le pair le lit dans la PR. Résumé : **la lentille bloque la progression de l'agent, sa présence bloque le merge, son verdict ne devient jamais un gate qui se rejoue.** Trois gardes contre le « retry-until-green » (relancer jusqu'à un verdict propre par hasard) : un bloqueur est **collant** — inscrit au rapport jusqu'à ce que l'agent le corrige ou le justifie, une relance ne l'efface pas ; la lentille est un **sous-agent distinct** de celui qui code ; une boucle qui ne converge pas est elle-même une entrée du journal de frictions (§8), ce qui lui donnera une borne le jour où elle coûte.
5. **Pas de pytest dans les hooks d'écriture.** Sur ce dépôt, la suite unitaire hermétique prend 18 à 34 s selon le cache (deux mesures sur `main`) ; un fichier de tests 5 s. Les tests tournent quand l'agent les lance (TDD), au commit (`pre-commit` sur `main` rejoue la suite unitaire), à la sortie du Build (`advance`), en CI. Les hooks d'écriture portent le lint.
6. **Rien ne juge une intention pour décider de passer.** On compare toujours un produit à un écrit antérieur.
7. **Une contrainte s'ajoute quand un incident l'a réclamée.** Le journal de frictions est la porte d'entrée ; il n'existe pas encore. Le palier 1 le crée.
8. **Tout ce qui peut faire corriger passe avant les preuves.** Une preuve se périme dès que l'arbre prouvé change. D'où Review avant Prove.
9. **Cap : borner le non-déterminisme des agents par du déterminisme, jusqu'à ce qu'un non-technicien n'ait plus à se poser la question.** Toute équipe ici est non technique — aucune relecture humaine ne garantit la correction d'un code. Donc chaque garde qui peut être un programme en devient un, et le consentement humain rétrécit vers l'intention seule, puis vers le rare. Un humain valide « voulons-nous ce changement », jamais « ce code est-il correct » : cette dernière question doit être répondue par la machine, ou rester sans réponse et l'assumer.

---

## 3. Où vit le dispositif

### Le constat

Le parcours est porté par six supports, aucun ne l'orchestre :

| Support | Contenu | Déclenché par |
|---|---|---|
| `scripts/paved_road_cli.py` + 4 cibles Makefile | `start`, `status`, `check`, `advance` | une commande |
| `lib/attestation.py` | états, checks, attestations, journal | la CLI |
| CI + `scripts/check_*.py` | les gates | GitHub |
| `.claude/settings.json` → `.claude/hooks/` (5 hooks, 6 fichiers dont un module partagé) | garde-fous d'écriture | Claude Code |
| `.claude/agents/design-coherence.md` | la seule lentille outillée | à la main |
| `CONTRIBUTING.md`, sept étapes en prose | l'orchestration | personne |

Deux problèmes de rangement, vérifiés :

- `.claude/skills` est un **lien symbolique vers `skills/`**, la boîte à outils de l'agent de production (celui qui répond aux analystes, embarqué dans l'image Docker par `COPY . .`). L'étage 08 a déposé `skills/smoke` dedans : un skill du parcours de développement est exposé à l'agent déployé.
- `gap-hunter` est cité dans le design, dans `l0-definition-of-done.md` et dans la DoD réelle (« la lentille `gap-hunter` a trouvé `DOD-5` »), mais aucun fichier ne le porte. `reverse-translation` n'apparaît que dans le design. L'étape Align repose sur une pratique tenue de tête.

### La décision proposée : un plugin dans le dépôt

Un répertoire `plugins/paved-road/` versionné avec le code, au format plugin Claude Code :

```
plugins/paved-road/
  .claude-plugin/plugin.json
  skills/
    paved-road/SKILL.md        ← routeur, invoqué par l'humain : /paved-road:paved-road
      align.md  build.md  review.md  prove.md  pr.md   ← un fichier par étape
    smoke/SKILL.md             ← déplacé depuis skills/smoke
  agents/
    gap-hunter.md              ← lentille d'Align, à créer
    design-coherence.md        ← déplacé depuis .claude/agents/ (nom scopé : paved-road:design-coherence)
    (lentilles suivantes, une par incident)
```

Pourquoi un plugin et pas `.claude/` : `.claude/` est partagé avec l'agent de production via le lien symbolique et via l'image. Le plugin est une unité nommée, chargée d'un bloc, invisible de l'agent déployé. Pourquoi dans le dépôt : les skills citent des cibles Makefile et des scripts qui évoluent avec le code ; un plugin externe dériverait.

Chargement : `make claude` = `claude --plugin-dir plugins/paved-road` (confirmé dans la doc, chargé en place, sans cache, le drapeau se répète). La marketplace locale déclarée dans `.claude/settings.json` est écartée au premier palier : elle copie le plugin dans un cache par utilisateur et fige sa version, ce qui contredit l'argument « pas de dérive ».

Ce qui reste dans `.claude/settings.json` du projet : les hooks (ils protègent toute session, et trois tournent aussi en production) et la liste `permissions.deny` (section 7). Ce fichier est embarqué dans l'image : la liste `deny` doit se limiter à ce qui ne gêne pas l'agent de production, qui écrit légitimement sous `.claude/` (voir section 7).

À ajouter à `.dockerignore` : `plugins/`. Vérifié : `.dockerignore` ne l'exclut pas aujourd'hui et le `Dockerfile` copie tout.

---

## 4. Les étapes, une par une

Lecture des tableaux : **agent** = ce que le skill ou les rules lui demandent ; **rattrapé par** = le vérificateur qui constate le manquement ; **où** = hook / commande locale / CI / GitHub ; **bloque** = empêche de continuer ; **palier** = 1, 2, 3, ou « déjà ».

### 4.1 Align — cadrer

**But.** Transformer un brief en contrat jugeable par le demandeur : `paved-road/<slug>/definition-of-done.md`, critères `DOD-1..N` en français, résultat observable au présent.

**Ce que voit le demandeur.** Les sections « Ce que je veux » et « Ce qui devra marcher », et au plus cinq décisions avec une réponse recommandée et sa conséquence observable. Pas la section « Sources lues », qui cite des fichiers de code : elle est pour l'agent et pour un owner `CODEOWNERS` qui voudrait aller au fond (et qui ira chercher quelqu'un de technique si besoin). Pas de question technique, pas de question dont la réponse ne change rien d'observable. Toutes les questions en une fois. La DoD réelle a déjà violé cette règle (une question sur le découpage des commits) : rien ne la rattrape, c'est écrit plus bas.

**Ce que fait l'agent (`align.md`) :**

1. Crée la branche (`<auteur>/feat/<slug>` ; le slug devient le nom du répertoire) et lance `make paved-road-start`.
2. Lit les sources selon les six règles R1–R6 (R1 : le code existant de la surface ; R2 : toute valeur chiffrée cite sa source de mesure ; R3 : glossaire ; R4 : façade des tableaux de bord ; R5 : décisions passées ; R6 : usage réel). R1 et R2 sont inconditionnelles. L'exploration lourde se délègue à un sous-agent de lecture.
3. Rédige les critères. Invariant permanent → guardrail, jamais dans la DoD ; contrainte propre à la demande → critère. Chaque `DOD-N` cite entre crochets la phrase du brief qu'il réalise : `DOD-1 — [du brief : « télécharger en markdown »] quand je clique sur Télécharger, un fichier .md se télécharge`. Sans phrase de brief rattachable, le critère est suspect et remonte au demandeur.
4. Lance la lentille **`gap-hunter`** (sous-agent, outils `Read, Grep, Glob`) : pour chaque critère, entrée vide, doublon, hors limites, état initial absent, accès concurrent. Ce qu'elle trouve devient un `DOD-N` proposé **avec sa réponse par défaut**, jamais une question. Elle liste ce qu'elle a lu.
5. Soumet au demandeur. Enregistre la validation (nom, date).
6. Commit de la DoD **en premier commit de la branche**.
7. `make paved-road-advance` → `build` si `verify_dod` sort en 0, puis : « étape franchie, ouvrez une nouvelle session ».

**Ce qui le rattrape :**

| L'agent devrait… | Rattrapé par | Où | Bloque | Palier |
|---|---|---|---|---|
| produire le fichier au bon endroit, `DOD-N` uniques, sections « Questions ouvertes » et « Validation », sans `<…>` de gabarit | `verify_dod` (`lib/attestation.py`) | `advance` | oui | déjà |
| idem, en CI | `check_paved_road.py` ne vérifie qu'un sous-ensemble : fichier présent, ≥ 1 critère, section « Questions ouvertes ». Ni unicité, ni « Validation », ni gabarit : il n'importe pas `verify_dod` | CI | oui, partiel | 1 : un seul analyseur |
| committer la DoD en premier | check d'antériorité (`git log --diff-filter=A`) ; contournable par réécriture d'historique, donc un signal, pas une garantie ; au palier 1, `pr.md` affiche au pair la date du premier commit de la DoD et celle du premier commit de code | `check_paved_road.py` | oui | 2 (signal en PR : 1) |
| ne pas modifier une DoD validée sans révision datée | diff de « Ce qui devra marcher » entre le commit de validation et HEAD : toute ligne changée porte une ligne « Révision AAAA-MM-JJ » | `check_paved_road.py` | oui | 2 |
| citer une source pour tout chiffre | nombre dans un `DOD-N` sans ligne dans « Sources lues » → avertissement | `verify_dod` | non | 2 |
| rester dans la borne (≤ 5 critères démontrés par navigateur) | `check_test_quality.py` refuse le sixième `test_dod_N` d'un module sous `browser/` | `make lint`, CI | oui | déjà |
| ne poser que des questions à effet observable | `gap-hunter` relit les décisions produites et signale toute décision dont la « conséquence observable » est vide ou technique ; au-delà de cinq, il refuse d'en soumettre plus et convertit le reste en critères à défaut | rapport `gap-hunter` | non (signal) | 2 |
| écrire une DoD fidèle au brief | **rien de déterministe** : aucun programme ne compare la DoD au besoin. La parade est humaine et vient à l'approbation : le pair relit « Ce qui devra marcher » ligne à ligne, pas seulement les verdicts (4.5), et chaque critère porte sa phrase de brief. C'est la faille d'entrée de tous les contournements honnêtes en aval, assumée faute de vérificateur possible | pair, à la PR | non | 1 (convention) |
| avoir réellement fait valider | rien. Mention textuelle que l'agent peut écrire. Dette assumée ; déclencheur de durcissement : première DoD « validée » dont le demandeur ne se souvient pas → validation par approbation d'une PR brouillon ouverte dès Align | — | — | 3 |
| lancer `gap-hunter` | rien au palier 1. Palier 2 : rapport committé sous `paved-road/<slug>/relectures/gap-hunter.md`, présence vérifiée | `verify_dod` | présence seulement | 2 |

`l0-definition-of-done.md` annonce la vérification des bornes sur le nombre total de critères ; `verify_dod` ne la fait pas. À l'inverse le code vérifie les placeholders, que le doc n'annonce pas.

### 4.2 Build — coder

**But.** Produire le code et ses tests, dans les conventions du dépôt, sans intervention humaine.

**Ce que voit le demandeur.** Rien. S'il relance `/paved-road:paved-road`, un état en français.

**Ce que fait l'agent (`build.md`) :**

1. Lit les rules chargées pour les fichiers qu'il touche (section 5).
2. TDD par tranche verticale : test rouge → code → test vert, en lançant le fichier de tests concerné (≈ 5 s). Jamais la suite complète à chaque cycle ; le `pre-commit` la rejoue au commit.
3. Ne touche ni aux seuils, ni aux workflows, ni aux scripts de vérification, ni aux tests existants pour les désarmer (section 7).
4. Quand il pense avoir fini : passe à Review (4.3). C'est `review.md` qui lance ensuite `make paved-road-advance` (`doctor`, `make lint`, `make security`, `make test`) → `prove`.

**Ce qui le rattrape :**

| L'agent devrait… | Rattrapé par | Où | Durée | Bloque | Palier |
|---|---|---|---|---|---|
| respecter les six règles que ruff ne sait pas dire (nom `_*.py`, docstring > 1 ligne, code commenté, `except Exception` sans `# Why:`, `MatomoAPI()` direct, SQL par f-string) | `check_python.py` | hook PreToolUse Edit/Write | ms | oui, session | déjà |
| écrire du Python conforme à ruff | `ruff_edited.py` | hook PostToolUse, sur le fichier | 0,04 s | oui, session | déjà |
| ne pas conclure un tour sur du lint rouge ou un test creux | `stop_lint_gate.py` | hook Stop | 0,4–2 s | oui, renvoyé au travail | déjà |
| ne pas utiliser `requests`, `urllib`, `unittest`, `psycopg2`, `os.environ` (8 API interdites), ni imports relatifs parents, ni appel HTTP sans timeout | ruff `TID251`, `TID252`, `S113` + `check_http_timeouts.py` (sur la pile ; `main` n'a pas encore ces règles) | `make lint`, CI `Lint & format` | 2 s | oui | déjà (pile) |
| ne pas laisser de route FastAPI sans authentification | `check_route_auth.py`, baseline gelée dans `gates.toml` (pile) | `make security`, CI `Security` | 1 s | oui | déjà (pile) |
| ne pas committer de secret | gitleaks | CI `Security` | — | oui | déjà |
| garder la suite unitaire verte | `make test` hermétique (1029 tests sans service, 18 à 34 s sur `main`) | `pre-commit`, `advance`, CI `Tests unit (sans services)` | 18–34 s | oui | déjà (`main`) |
| garder les tests d'intégration verts | job `Tests integration (Postgres + Redis)` (`-m "integration or e2e"`, 49 marqueurs sur `main`) | CI, requis | — | oui | déjà (`main`) |
| couverture ≥ plancher, 90 % sur le diff | job `Couverture fusionnée + diff-cover` | CI, requis | — | oui | déjà (`main`) |
| accompagner tout changement de modèle d'une migration, sans `NOT NULL` avant remplissage | `alembic check` + `check_migration_backfill.py` (pile) | CI `Migrations` | — | oui | déjà |
| un test par comportement (rule `tests.md`) | rien ne mesure « un test par modification » ; 90 % sur le diff est l'approximation | CI | oui | déjà |
| prouver un critère avec un test qui parle bien de ce critère | la preuve d'un `DOD-N` doit être un test dont l'identifiant contient `dod_N` (convention déjà portée par `check_test_quality`) ; un `test_health` générique ne peut pas prouver `DOD-1`. Ne juge pas la pertinence sémantique — un programme ne le peut pas — mais ferme le « test vert au hasard » | `prove()`, CI | oui | 1 |
| ne pas désarmer un test (supprimer, `skip`, `xfail`, affaiblir une assertion) | palier 1 : `check_test_quality.py` refuse un `skip`/`xfail` ajouté dans le diff sans `# Why:`, et **échoue** si une assertion d'un test préexistant touché par le diff est affaiblie (comparée à sa version sur la base) : reprise ou `break-glass`, pas un simple signal. Palier 2 : le compte des tests supprimés et des assertions modifiées s'ajoute à la description de PR (règle pour le pair : un compteur non nul, on ne signe pas avant d'avoir fait regarder par quelqu'un de technique) | `make lint`, CI ; script de PR | oui (affaiblissement), signal (compte) | 1 / 2 |
| pas de SQL par concaténation | ruff `S608` en observation sur la pile ; `check_python` l'attrape en session | `make lint` | non | 2 → bloquant après zéro faux positif sur N runs |

**Ce que la pile doit reprendre de `main` avant tout.** Sur `main` depuis le 20 août : `make test` est hermétique (`DATABASE_URL= REDIS_URL=`, 18 à 34 s, aucun service), la CI a trois jobs de tests au lieu d'un (`Tests unit (sans services)`, `Tests integration (Postgres + Redis)`, `Couverture fusionnée + diff-cover`), tous trois requis, et `pre-commit` rejoue `make test` à chaque commit touchant un `.py`, une fois `make hooks` lancé. La pile, elle, a encore un job `Tests` unique, un `conftest` qui exige Postgres à la collecte, et une `tests.md` qui dit l'inverse. Le brief du 19 août (« 47 tests d'intégration jamais lancés ») était vrai sur la pile, il est faux sur `main`. Le rebase touchera `ci.yml`, `Makefile`, `pyproject.toml`, `tests/conftest.py`, `.claude/rules/tests.md`.

**Pourquoi aucun pytest dans les hooks Claude Code.** Un fichier de tests, 5 s ; la suite hermétique, 18 à 34 s. Un hook PostToolUse qui lance pytest rendrait chaque écriture insupportable ; un hook Stop qui lance la suite ajoute une demi-minute à chaque fin de tour, y compris quand l'agent s'arrête pour poser une question. Le `pre-commit` de `main` fait déjà ce travail au bon moment : au commit, une fois par tranche. On ne double pas.

### 4.3 Review — relire

**But.** Comparer le code au contrat, et regarder ce qu'aucun test n'avait prévu. Tout ce qui peut faire corriger passe ici, avant les preuves. Review se joue dans l'état `build` ; **la lentille y est une boucle de fix bloquante** : l'agent ne franchit `build → prove` qu'une fois les bloqueurs traités.

**Ce que voit le demandeur.** Si un smoke a lieu, son navigateur qui suit le parcours, dans sa session ; il ne décide rien. À la PR : la review app et les captures.

**Ce que fait l'agent (`review.md`), dans cet ordre :**

1. Écrit le diff de la branche dans `/tmp/paved-road/<slug>/diff.patch` et lance la lentille **`paved-road:design-coherence`** (sous-agent, outils `Read, Grep, Glob` ; c'est le skill qui lui fournit le diff, il n'a pas besoin de `git`) : pour chaque `DOD-N`, quel code le réalise ; quel code ne se rattache à aucun critère ; le code fait-il autre chose que ce que le critère décrit. Rapport en français, avec la liste de ce qu'il a lu.
2. Traite chaque bloqueur du rapport : corrige le code, ou écrit sous le bloqueur pourquoi ce n'en est pas un. Relance la lentille — un bloqueur déjà inscrit ne disparaît pas d'une relance, il faut l'avoir adressé. La boucle tourne sans plafond, jusqu'à ce qu'aucun bloqueur nouveau ne subsiste ; une boucle qui ne converge pas se règle par une interruption humaine et devient une entrée de rétro. C'est le seul cran où le verdict d'une lentille arrête l'agent — mais il ne l'arrête qu'en session, jamais en CI.
3. En dernier, si `scripts/smoke.py plan` dit qu'une interface est touchée : une passe de **smoke**, une capture par critère, un `rapport.md`. Le smoke vient après les corrections parce que `plan` refuse une seconde passe sur la même empreinte d'interface : toute correction rouvrirait une passe.
4. `make paved-road-advance` → `prove`, puis « étape franchie, ouvrez une nouvelle session ».

**Une limite à dire tout de suite.** Le smoke pilote le Chrome de la machine via l'extension Claude in Chrome : il exige une session interactive avec un humain présent. C'est la seule étape qui ne tourne pas la nuit. Palier 3 : bascule sur Playwright headless. D'ici là, la review app donne au pair le moyen d'essayer lui-même.

**Ce qui le rattrape :**

| L'agent devrait… | Rattrapé par | Où | Bloque | Palier |
|---|---|---|---|---|
| lancer `design-coherence` et en traiter les bloqueurs | palier 1 : `review.md` la lance et l'agent ne demande `advance` vers `prove` qu'après avoir adressé chaque bloqueur (boucle de fix en session). Palier 2 : le rapport est committé sous `paved-road/<slug>/relectures/design-coherence.md`, rattaché aux **empreintes d'arbre** (pas au SHA de HEAD, qui change dès qu'on commit le rapport), et la CI en exige la présence à jour | session (bloqueurs) ; `advance` puis CI (présence) | oui | 1 (fix loop) / 2 (présence CI) |
| faire un smoke si une interface est touchée | `scripts/smoke.py verify` existe (refuse un binaire committé, exige `rapport.md`) mais tout vit sous `~/.cache`, hors dépôt : vérifiable en local seulement, jamais en CI | `advance` | local | déjà ; 2 pour le verdict de `plan` committé |
| adresser un bloqueur, pas le faire disparaître | le bloqueur est collant : inscrit au rapport tant qu'il n'est pas corrigé ou justifié ; une relance ne le retire pas ; la lentille est un sous-agent distinct, l'agent ne réécrit pas son verdict | rapport de lentille | oui, en session | 1 |
| ne committer ni capture ni donnée réelle | `verify_content` : tout non-`.md`, > 16 Kio, image, base64 sous `attestations/`. **Limite réelle à écrire** : `verify_content` ne juge que la forme, et le seul masquage de données est le NIR (`lib/pii.py`) — un email ou un nom de candidat dans une sortie rejouée passe tel quel, sur un dépôt public. Comme `retro.md` est exigé dès le palier 1 et que R6 pousse l'agent à citer l'usage réel, le scan s'étend à tout `paved-road/<slug>/**` **dès le palier 1** (≈ 5 lignes), pas au palier 2 | `advance`, CI | oui | 1 |

**Lentilles de Review, catalogue et règle d'ouverture.** Toutes bloquent de la même façon — boucle de fix en session, présence vérifiée en CI. Une seule est ouverte d'emblée ; les autres s'ouvrent une par une, sur une entrée du journal de frictions qui nomme l'incident et explique pourquoi aucun vérificateur déterministe ne pouvait le voir. Une lentille de haut niveau (cohérence de la feature) et une lentille de code (sécurité, architecture) suivent le même régime ; ce qui change, c'est la question posée. Le palier est un pronostic :

| Lentille | Question | Ouverture | Palier |
|---|---|---|---|
| `design-coherence` | le code fait-il ce que la DoD dit, ni plus ni moins ? | ouverte | déjà |
| `surgical-changes` | reformatage, refactor adjacent, suppression non demandée ? | sur incident ; probable tôt | 2 |
| `security-auditor` | autorisation, injection, secret, PII dans les logs ? | **conditionnelle** : la DoD répond oui à « touche des données de candidats, une route, un upload, une nouvelle source ? » | 2 |
| `dod-test-fidelity` | un `test_dod_N` est-il un vrai parcours ? | avec le premier vrai e2e | 2 |
| `test-quality`, `edge-case-hunter`, `abstraction-quality`, `legal-compliance`, `query-cost`, `knowledge-drift` | voir le design | sur incident | 3 |

Jamais des lentilles : la conformité aux `.claude/rules/` (c'est ruff) et la sûreté des migrations (c'est `alembic check`).

### 4.4 Prove — prouver

**But.** Une preuve par critère, produite par une commande et son code de sortie, rattachée au contenu prouvé.

**Ce que voit le demandeur.** Le verdict par critère, dans la description de PR : démontré, non démontré, périmé.

**Ce que fait l'agent (`prove.md`) :** pour chaque `DOD-N`, `make paved-road-advance DOD=DOD-N CMD='…'`. `advance` exécute la commande, écrit `attestations/DOD-N.md` (commande, code de sortie, sortie tronquée, empreintes d'arbre de `web`, `lib`, `scripts`, `skills`, `alembic`, `tests`, verdict), refuse si un chemin prouvé a des modifications non committées. `skills` entre dans les empreintes : sans lui, réécrire le corps d'un `SKILL.md` après attestation ne périmerait rien (le principe 8 serait faux sur ce tiers du périmètre).

**Quelle preuve pour quel critère** (à écrire dans `prove.md`, palier 1) :

| Le critère parle de… | Forme de preuve admise | Rejouable en CI ? |
|---|---|---|
| un comportement du code (`web/`, `lib/`) | un test unitaire ciblé, `uv run --frozen pytest tests/… -k …` | oui |
| un parcours dans le navigateur | un `test_dod_N` sous `browser/`, joué par le workflow `E2E` ; l'attestation porte le verdict `démontré (E2E)` et **est marquée non rejouable** : `check_paved_road.py` la reconnaît à sa commande (`pytest browser/…`) et ne la rejoue pas, sinon elle échouerait faute de Playwright et d'application servie dans le job | non, par le job E2E seulement |
| une migration | `alembic check` + migration jouée | oui |
| un `SKILL.md`, un fichier `knowledge/` | frontmatter valide, chemins cités existants ; preuve comportementale différée (evals, palier 3) | oui |
| un chiffre (volumétrie, temps) | mesure en nightly, hors chemin bloquant ; l'attestation porte le verdict `démontré (nightly)`, non rejouée par le job requis ; la DoD le dit d'avance | non |

**Ce qui le rattrape :**

| L'agent devrait… | Rattrapé par | Où | Bloque | Palier |
|---|---|---|---|---|
| démontrer chaque critère | `verify_attestations` : critère sans attestation, code ≠ 0, empreinte absente ou périmée, attestation orpheline | `advance`, CI « Ce qui devait marcher » | oui | déjà |
| ne pas fabriquer une attestation | la CI rejoue la commande et compare le code de sortie | CI | oui | déjà (job), **pas encore requis** |
| ne pas prouver avec une commande vide ou détournée (`true`, `pytest --version`, `pytest --collect-only`, `pytest -k test_health` sans rapport avec le critère) | palier 1 (≈ 40 lignes) : même exécuteur local et CI (sans shell) ; liste fermée de préfixes ; `--collect-only` et `--co` interdits ; la commande doit **exécuter** au moins un test dont l'identifiant contient `dod_N` (croise la convention du Build). Ne prouve pas la pertinence du corps du test — aucun programme ne le peut — mais ferme la commande décorative | `prove()`, CI | oui | 1 |
| ne pas utiliser la même commande pour deux critères (la DoD réelle le fait : `DOD-2` et `DOD-4`) | avertissement dans `verify_attestations` | `advance` | non | 2 |
| ne rien ranger d'autre que du texte sous `attestations/` | `verify_content` | `advance`, CI | oui | déjà |
| prouver sur le dernier état | empreintes d'arbre | `advance`, CI | oui | déjà |

Écart de code à corriger : `check_paved_road.py` rejoue avec `shell=True`, `lib/attestation.py` avec `shlex.split` ; deux analyseurs de critères aussi. Un seul des deux côtés.

### 4.5 PR → main — un pair valide

**But.** Un second non-technicien approuve sur les preuves et les critères, jamais sur le diff. GitHub tient le reste.

**Ce que voit le pair.** La description de PR : une ligne par `DOD-N` avec son verdict, le lien vers la preuve, l'URL de la review app (déployée par le job `Review app` de `main` sur chaque PR non brouillon, visible dans l'encart de déploiement une fois la CI verte ; base vide, donc rien à voir pour une fonctionnalité de données), les captures du smoke, la date du premier commit de la DoD et celle du premier commit de code (règle de lecture : du code daté avant le contrat, on ne signe pas — on va d'abord chercher un avis technique), ce qui n'a pas été démontré. Au palier 2 s'ajoutent les compteurs : tests supprimés, assertions modifiées, fichiers protégés touchés, avec la règle : un compteur non nul, on ne signe pas avant d'avoir fait regarder par quelqu'un de technique. Il doit savoir aussi que si la PR touche une zone critique ou l'outillage, son approbation ne suffira pas : un owner `CODEOWNERS` devra consentir aussi. Cet owner est non technique comme lui ; la couche 3 lui rend le changement en français, et s'il le juge trop technique, c'est à lui d'aller chercher quelqu'un de technique — le dispositif ne le fait pas à sa place.

**Ce que fait l'agent (`pr.md`) :** ouvre la PR avec DoD, journal, attestations, relectures, rétro ; génère la description d'après un gabarit (palier 1) puis par script, identique quel que soit l'agent (palier 2). Le gabarit de PR actuel du dépôt (ticket Notion, cases Conventional Commits, « Comment tester ») est remplacé par celui-ci.

**Ce qui garantit — ici rien ne dépend de l'agent :**

| Garantie | Mécanisme | État vérifié le 22 août | Palier |
|---|---|---|---|
| rien de rouge n'atteint `main` | ruleset « protect default branch », **7 checks requis** : `Lint & format`, `Security`, `Tests unit (sans services)`, `Tests integration (Postgres + Redis)`, `Couverture fusionnée + diff-cover`, `Migrations`, `Docker` ; `strict: true` | en place | déjà |
| chaque critère démontré | check « Ce qui devait marcher » requis | job sur la pile, **pas dans la liste requise** ; nécessite `break-glass` pour les PR hors parcours (étages 08 et 09 touchent `skills/` et `lib/` sans DoD ; hotfixes ; dependabot) | 1 |
| le label `break-glass` posé par un humain, pas par l'agent | l'agent a le droit `write` et pourrait faire `gh pr edit --add-label break-glass` : la règle `Bash(gh * --add-label*)` (et `--label`) est dans le `deny` (section 7), et le check refuse un `break-glass` dont l'API dit qu'il a été posé par l'auteur de la PR. Sans ça, l'agent lève lui-même le seul gate qui vérifie ses preuves | `deny` + `check_paved_road.py` | oui | 1 |
| un humain approuve | 1 approbation, fils de discussion résolus | en place ; **`dismiss_stale_reviews_on_push: false`** (un push après approbation ne la retire pas) et **`require_last_push_approval: false`** (le dernier push n'a pas à être approuvé par quelqu'un d'autre que son auteur) : l'agent peut pousser après le oui du pair sans re-revue. C'est le trou exact du parcours ; l'un des deux au moins à cocher | 1 |
| les zones critiques ont un relecteur désigné | `CODEOWNERS` (19 chemins, 3 titulaires, fichier sur la pile, pas encore sur `main`) + `require_code_owner_review` | **réglage à `false`** | 1 |
| la liste des checks requis ne dérive pas de la CI | `check_required_checks.py` | **corrigé le 27 août** : lit `/rules/branches/main` (le ruleset) au lieu de la protection classique, et échoue si l'API refuse au lieu de rendre 0 — un check aveugle est vert quoi qu'il arrive. Vérifié en réel : il détecte les trois jobs de tests de `main` requis mais absents du `ci.yml` de la pile | fait |
| `CODEOWNERS` sans entrée inerte | `codeowners/errors` en CI | en place (pile) | déjà |
| un job vidé mais gardant son nom | non couvert ; parade : `CODEOWNERS` sur `.github/workflows/` **et** sur `Makefile` (la CI appelle ses cibles), réglage coché | — | 1 |
| personne ne contourne | bypass `louije` **en mode `pull_request`** (contournement possible, mais via une PR, donc visible) | en place | décision 8 |
| protection classique résiduelle | à côté du ruleset, une protection de branche classique subsiste : `Lint & format` seul requis, 0 approbation, force-push autorisé, mais aussi une restriction de push directe et l'historique linéaire, que le ruleset ne reprend pas. Redondante pour les checks et l'approbation, source de confusion, et c'est elle que lit le script | reporter ses deux règles utiles dans le ruleset, puis la supprimer | 1 |

Un point de fonctionnement, et il est plus lourd qu'il n'y paraît : `strict: true` oblige à rebaser avant merge. Quand deux PM travaillent en parallèle, le merge de la première périme les empreintes d'arbre de la seconde dès qu'il touche `web`, `lib`, `scripts`, `skills`, `alembic` ou `tests` → le check « Ce qui devait marcher » passe au rouge → **re-`prove` intégral**, et si l'interface a changé, **re-smoke avec un humain présent**. Le conflit de rebase lui-même est technique (c'est l'agent qui rebase, pas le PM), mais un conflit qui touche un choix métier n'entre dans aucune famille du §9 : à traiter comme une question métier (famille C) qui remonte au demandeur. Et si l'un des réglages de la ligne « un humain approuve » est coché, chaque rebase redemande l'approbation du pair. À dire au pair, et à limiter en sériant les parcours qui touchent les mêmes surfaces.

### 4.6 À tout moment

`/paved-road:paved-road` lit `make paved-road-status` et répond en français : où on en est, quels critères sont démontrés, ce qui bloque et qui peut débloquer. Palier 1, un gabarit dans le skill.

---

## 5. Les règles, scopées par chemin

Claude Code charge un fichier de `.claude/rules/` à chaque session s'il n'a pas de frontmatter, ou quand l'agent **lit** un fichier correspondant s'il porte `paths:`. Une règle scopée ne se charge pas quand l'agent crée un fichier neuf sans en avoir lu un semblable, ce qui est fréquent en TDD. D'où : on scope ce qui est long et spécifique, on laisse `code.md` et `tests.md` chargés toujours.

| Règle | `paths:` | Vérifiée par | Où |
|---|---|---|---|
| `code.md` | aucun (toujours) | ruff, `check_python.py`, `check_http_timeouts.py` | hook + `make lint` + CI |
| `tests.md` | aucun (toujours) ; **contenu à reprendre de `main`** | `check_test_quality.py`, ruff `PT010/012/015/017/027`, `diff-cover` | `make lint` + CI |
| `sql.md` | `web/**`, `lib/**`, `alembic/**` | `check_python.py`, `alembic check`, `check_migration_backfill.py`, ruff `S608` (observation) | hook + CI |
| `api.md` | `lib/**`, `skills/**`, `web/**` | `check_python.py`, `check_http_timeouts.py` ; « > 5 requêtes segmentées » : personne | hook + `make lint` |
| `securite.md` | `web/**`, `lib/**`, `alembic/**`, `paved-road/**` | bandit, gitleaks, `check_route_auth.py`, `verify_content` | CI |
| `zones-critiques.md` | sa propre liste (17 entrées, 18 chemins ; elle diffère de `CODEOWNERS`, qui en a 19 ; les deux fichiers l'assument) | `CODEOWNERS` + réglage coché ; le message « zone critique » demandé à l'agent : personne | GitHub |
| `review.md` | `.github/**`, `paved-road/**` | grille pour relecteur humain | — |

Une ligne en tête de chaque fichier : « Vérifié par : … » ou « Vérifié par : personne ».

---

## 6. Les tests : où et quand

Pour un lecteur non technique : « les tests » désignent trois choses. Les tests unitaires vérifient une fonction, il y en a un millier, ils tournent en moins d'une demi-minute sans rien d'autre que le code. Les tests d'intégration ont besoin de la base de données et d'un second service (la file d'attente), la CI les fournit. Les tests de bout en bout pilotent un navigateur : un socle de cinq parcours communs à l'application, plus au plus cinq par fonctionnalité. Les preuves sont à part : une commande par critère, rejouée en CI.

| Moment | Ce qui tourne | Durée mesurée | Besoin | Bloque |
|---|---|---|---|---|
| à chaque écriture (hooks) | ruff sur le fichier, `check_python` | < 0,1 s | rien | oui, session |
| fin de tour (hook Stop) | ruff + format sur `web lib tests scripts`, `check_test_quality` sur `tests` | 0,4–2 s | rien | oui, session |
| pendant le Build, à la main de l'agent | `pytest tests/test_x.py -q` | ≈ 5 s | rien (`main`) | non |
| au commit (`pre-commit`, `main`, après `make hooks`) | ruff, `check_test_quality`, `make test` hermétique | 18–34 s | rien | oui (`--no-verify` contourne) |
| sortie du Build (`advance`, pile, avant rebase) | `doctor`, `make lint`, `make security`, `make test` | non mesuré (≤ 9 s de timeouts) + 2 s + ≈ 1 s + ≈ 70 s | Docker pour `doctor` ; Postgres et Redis pour `make test` tant que la pile n'a pas repris le `conftest` de `main` | oui, état |
| pre-push (pile, avant rebase) | ruff + unitaires | ≈ 60 s | Postgres | non (`--no-verify`) ; redondant avec `advance`, à faire sauter quand le journal montre un `advance` réussi sur HEAD |
| CI `Tests unit (sans services)` | 1029 tests + couverture | — | rien | oui |
| CI `Tests integration (Postgres + Redis)` | `-m "integration or e2e"` | — | services CI | oui |
| CI `Couverture fusionnée + diff-cover` | fusion, plancher, 90 % du diff | — | — | oui |
| CI `E2E` (workflow séparé) | `browser/`, Playwright | — | app servie par le job | non, hors checks requis jusqu'à stabilité |
| nightly | `pip-audit`, E2E | — | réseau | non |

Mesures : `main` à `356a5c0` pour la suite hermétique (17 s et 34 s sur deux runs) ; `paved-road/02-instrumentation` pour ruff, le fichier unique (5,7 s avec base) et `make security` (même cible que sur `main`, avec `pip-audit` : 21 s à chaud, 229 s à froid, et un échec sur une CVE de `pip` lui-même). La pile a sorti `pip-audit` vers un job nightly : `make security` y prend ≈ 1 s. Le job `Security` est celui qui échoue le plus sur `main` (27 échecs sur 112 runs non annulés depuis mai, un sur quatre) : cause `pip-audit`, traitée par la pile. À re-mesurer après merge.

---

## 7. Empêcher l'agent de modifier ses propres outils

Quatre couches, du plus proche de l'agent au plus loin. La dernière est la seule hors de portée de l'agent — mais elle apporte un **consentement**, pas une revue d'expert : les owners sont non techniques (principe 9). Ils autorisent qu'un changement existe ; ils ne certifient pas qu'il est correct. La correction d'un changement technique repose sur les couches déterministes et les lentilles bloquantes, jamais sur eux.

| Couche | Mécanisme | Ce qu'il refuse | Limite | Palier |
|---|---|---|---|---|
| 1. Permissions de session | `permissions.deny` dans `.claude/settings.json`, règles `Edit(...)` seulement (les règles `Write(...)` sont acceptées mais jamais consultées) ; chemins ancrés à la racine du projet (`Edit(/gates.toml)`) | l'édition par les outils de fichiers, et les redirections `>`, `>>`, `2>` vers ces chemins (la cible d'une redirection est traitée comme une écriture) ; tient en tout mode, y compris dans les sous-agents | `sed -i`, `tee`, `python -c "open(...).write()"` passent ; `.claude/` est déjà un chemin protégé nativement (l'outil demande confirmation), le `deny` le rend bloquant | 1 |
| 2. Bac à sable | `sandbox.enabled` (macOS via Seatbelt, Linux via bubblewrap ; rien à installer sur macOS) avec `sandbox.filesystem.denyWrite` sur les chemins d'**outillage** (`.claude/**`, `.github/**`, `gates.toml`, `Makefile`, `scripts/check_*.py`, `lib/attestation.py`, `plugins/**`) — **pas** sur `paved-road/*/attestations/**` ni `*/journal/**`, qu'`advance` (un processus enfant) doit écrire ; ces deux-là restent en couche 1 seulement (l'agent ne les édite pas à la main, `advance` les écrit) | ce que la couche 1 laisse passer : `sed -i`, `tee`, scripts Python, tout processus enfant, sur l'outillage | un `git merge` qui doit remplacer un fichier interdit échoue et doit être relancé hors bac à sable | 2 |
| 3. Annotation CI | `check_protected_paths.py` : si le diff touche un chemin protégé, écrit dans la description de PR, **en français**, ce que la machinerie change — et surligne tout affaiblissement de garde-fou (« abaisse le seuil de 71 % à 60 % », « retire l'authentification d'une route »). Ne bloque pas et n'exige pas de label : il rend le changement lisible pour que l'owner (non technique) consente en connaissance de cause | une modification d'outillage noyée dans une PR, invisible à un non-technicien | descriptif, pas un gate ; le gate est la couche 4 | 2 |
| 4. Consentement GitHub | `CODEOWNERS` + `require_code_owner_review: true` : toute PR qui touche un chemin protégé exige l'approbation d'un owner, qui n'est jamais l'auteur de la PR (donc jamais l'agent). Ajouter `Makefile`, `pyproject.toml`, `.githooks/`, `scripts/`, `lib/attestation.py`, `plugins/paved-road/` aux 19 chemins. L'owner consent en français (couche 3) ; s'il se sent hors de sa profondeur, **c'est lui qui va chercher quelqu'un de technique**, hors dispositif | l'agent qui réécrit les trois couches sans qu'un humain dise oui ; un affaiblissement de garde-fou qui passe inaperçu | ne garantit pas la correction du code, seulement le consentement ; le bypass `pull_request` passe au travers, via une PR visible | 1 |

Les commandes qui comptent vont dans la couche 1 aussi, comme règles `Bash` : `git push --force*`, `git commit * --no-verify*`, `git commit -n *`, `git -c core.hooksPath=*`, `gh * --add-label*`, `gh * --label*` (pour que l'agent ne se pose pas lui-même un `break-glass`).

**Le revers : sans liste `allow`, le PM est noyé sous les invites.** Un `deny` n'auto-approuve rien ; en mode par défaut, chaque `make`, `pytest`, `git`, `gh` de la session déclenche une demande d'autorisation qu'un non-technicien ne sait pas juger. Il faut donc, au palier 1, **une liste `allow`** couvrant les commandes du parcours (`Bash(make *)`, `Bash(uv run --frozen pytest*)`, `Bash(git add*)`, `Bash(git commit*)` hors `--no-verify`, `Bash(gh pr create*)`, `Bash(gh pr view*)`…) ; le `deny` reste prioritaire sur l'`allow`, donc les contournements listés ci-dessus restent bloqués. Sans cette liste, le parcours nominal est impraticable pour la cible visée.

**Chemins protégés** (une liste, dans `gates.toml`, que les couches 3 et 4 recopient) : `.claude/settings*`, `.claude/hooks/**`, `.claude/rules/**`, `.claude/agents/**`, `.github/**`, `.githooks/**`, `gates.toml`, `Makefile`, `scripts/check_*.py`, `scripts/paved_road_cli.py`, `lib/attestation.py`, `plugins/paved-road/**`, `paved-road/*/attestations/**`, `paved-road/*/journal/**`. `pyproject.toml` n'est pas dans la couche 1 (une fonctionnalité peut ajouter une dépendance) ; il est dans la couche 4. La couche 1 ne met pas `.claude/**` en entier : l'agent de production, qui tourne avec ce fichier, écrit légitimement sous `.claude/`.

Ce qui n'est pas couvert et qu'on écrit franchement : les owners étant non techniques, aucune approbation ne garantit qu'un changement de code critique est correct — elle garantit qu'un humain l'a voulu et l'a vu. La correction, sur ces zones, ne tient qu'au déterministe (tests, rejeu, lentilles bloquantes) ; ce que le déterministe n'attrape pas reste un angle mort, prix assumé d'une équipe sans développeur (section 14). Autres limites : l'agent doit tourner avec le jeton du demandeur, qui n'est pas owner (sinon il s'auto-approuve) ; le bypass `pull_request` d'un compte passe au travers, via une PR visible. `retrait-spec-kit.md` renvoie « revue obligatoire » vers `CODEOWNERS` : tant que la case n'est pas cochée, le renvoi pointe vers rien.

Conséquence pratique : quiconque modifie l'outillage à la main (au montage, ou une personne technique appelée pour l'occasion) le fait dans une session lancée avec `--setting-sources user` (ignore les réglages du projet), ou à la main ; la PR qui en résulte passe par `CODEOWNERS`. Et la couche 1 se pose **en dernier** dans le palier 1, sinon elle bloque la création du plugin et l'édition des rules par l'agent qui fait le chantier.

---

## 8. Le journal de frictions

La seule porte d'entrée autorisée pour ajouter une lentille ou une contrainte, et il n'existe sur aucune branche.

**Palier 1 — en prose, sans code.** À la fin de chaque parcours, avant la PR, l'agent écrit `paved-road/<slug>/retro.md` d'après quatre questions : où il a tourné en rond ; ce qui manquait dans le contexte ; quelle règle l'a gêné sans raison ; quelle contrainte lui a manqué. Committé avec le reste. `pr.md` l'exige avant d'ouvrir la PR. Comme il est obligatoire dès le palier 1 sur un dépôt public, son innocuité est vérifiée dès le palier 1 (`verify_content` étendu à `paved-road/<slug>/**`, 4.3), pas au palier 2 : un récit peut contenir un email ou un nom cité pendant Align.

**Palier 2 — les chiffres à côté.** `lib/paved_road.py` calcule déjà coût, durée, reprises humaines et bruit des gates (`make paved-road-baseline`). Y ajouter par parcours : échecs d'`advance` par famille, lus dans `paved-road/*/journal/`. La rétro fournit la matière, le journal les chiffres.

**Comment une friction devient un check.** L'équipe (non technique) lit périodiquement les `retro.md` et la ligne de base, et convertit une friction récurrente — comme n'importe quelle demande, en la faisant construire par le parcours : écrire un check est du code, l'agent l'écrit. Deux voies : si un programme peut voir la friction → un vérificateur, sinon → une lentille (qui bloque en boucle de fix en session, principe 4, sans rejouer son verdict en CI). Ce qui rend ça sûr sans lire le code, c'est le **cliquet** : un nouveau vérificateur entre en **observation** (`--exit-zero`, il compte sans bloquer, comme `S608`), et on ne l'arme qu'après l'avoir vu réagir correctement sur des cas réels — un jugement empirique qu'un non-technicien porte très bien (« a-t-il bien réagi ce mois-ci ? »). La décision est écrite dans `docs/plans/` avec l'entrée qui l'a déclenchée. Une réserve honnête : un check pour un incident rare peut s'armer sans avoir jamais fait feu ; « N runs sans faux positif » ne prouve pas qu'il attrape, seulement qu'il ne gêne pas.

Pas de journal JSONL structuré comme akria : leurs hooks y écrivent à chaque refus ; ici les refus sont rares et lisibles dans le journal d'état.

---

## 9. Familles d'échec, questions, blocages

Chaque check déclare sa famille ; elle commande la suite.

| Famille | Exemple | Suite |
|---|---|---|
| A réparable | test rouge, lint, preuve périmée | l'agent reprend. Compteur d'échecs enchaînés en observation ; au plafond (palier 2) : pause, état en français au demandeur, et signalement technique ; pas une question au demandeur, qui n'a rien à répondre à un lint rouge |
| B environnement | Postgres absent, Matomo injoignable, réseau coupé | l'agent diagnostique (`make doctor`) et tente les réparations sûres lui-même : démarrer les services (`docker compose up -d db redis`), réessayer un appel transitoire. Ce qu'il ne peut pas faire seul, il le rend en une phrase actionnable au demandeur (« ouvre Docker Desktop ») ; une panne amont (Matomo/Metabase down) se constate et s'attend, il n'y a personne à qui escalader |
| C question métier | critère ambigu, infaisable découvert tard, conflit de rebase à trancher | question au demandeur, deux options au moins en résultats observables. Si un critère se révèle infaisable en plein Build : l'agent n'édite pas la DoD (elle est protégée), il ajoute sous le critère une ligne « Révision AAAA-MM-JJ » motivée, la fait revalider, et repart. `paved-road-cli` gagne un verbe `revise` au palier 2 ; au palier 1, c'est une édition manuelle du fichier DoD, hors `deny` (la DoD n'est pas un chemin protégé, seules les attestations le sont) |
| D interdit | abaisser un seuil, supprimer un test, migration destructive, binaire sous `attestations/` | arrêt ; `break-glass` posé par un humain technique, journalisé |

L'agent peut se mettre en pause ; il ne peut jamais se débloquer lui-même. Une boucle de fix de lentille (§4.3) qui ne converge pas n'a pas de plafond automatique : elle s'interrompt à la main et remonte en famille C (pour design-coherence, un bloqueur qui résiste signale souvent une DoD bancale) ou D (sécurité, architecture). `l1-attestation.md` et `l2-quality-gates.md` donnent deux définitions de C et D : une seule table, citée par les autres.

---

## 10. Trois paliers de mise en place

Ces paliers 1-2-3 n'ont rien à voir avec les fichiers `l0-…` à `l6-…` du dépôt, qui seront renommés (palier 2). Le palier 1 doit permettre un premier parcours réel en quelques jours. Le montage — rebaser la pile, écrire les checks Python, relire le code du dispositif lui-même — est fait par toi (Clément), en une fois. C'est un travail technique et ponctuel, il n'installe aucun rôle permanent. Une fois le dispositif en place, plus aucune relecture n'exige de compétence de code (principe 9).

### Palier 1 — démarrer

Dans l'ordre, parce que l'ordre compte :

| # | Chantier | Nature | Dépend de |
|---|---|---|---|
| 1 | **Rebaser la pile sur `main`** (après #181, #185, #191) : conflits attendus sur `ci.yml`, `Makefile`, `pyproject.toml`, `tests/conftest.py`, `tests.md` ; reprendre la découpe unit/integration/coverage | git, humain technique | — |
| 2 | Sortir les six étages sans PR (04 → 09), une PR par étage ; les étages 08 et 09 touchent `skills/` et `lib/` sans DoD : label `break-glass` | processus, 3 relecteurs | 1 |
| 3 | GitHub, par l'administrateur du dépôt : cocher `require_code_owner_review` et `require_last_push_approval` ; reporter puis supprimer la protection classique résiduelle ; inscrire « Ce qui devait marcher » dans les checks requis après merge de l'étage 06 ; comptes GitHub avec droit d'écriture pour les deux PM | réglages | 2 |
| 3 bis | Préparer le poste de chaque PM : dépôt cloné, `make setup` (Docker, `.env`, base), Claude Code, extension Claude in Chrome, `gh auth login`. Enrichir `align.md`/`build.md` pour que l'agent diagnostique et répare les pannes d'environnement lui-même (famille B) plutôt que d'attendre un humain | main technique au montage, une heure par poste | — |
| 4 | ~~`check_required_checks.py` : lire le ruleset~~ — **fait le 27 août**, 24 tests | Python | 1 |
| 5 | `prove()` : même exécuteur local/CI ; `--collect-only` interdit ; la commande doit exécuter un test dont l'id contient `dod_N` ; attestations navigateur/nightly marquées non rejouables et non rejouées par `check_paved_road.py` ; un seul analyseur de critères | Python, ≈ 60 lignes | 1 |
| 6 | Lever dans `code.md` l'interdit de commit/push pour les branches du parcours (le design le prévoyait ; sans lui, `align.md` et `pr.md` sont impossibles) | markdown | — |
| 7 | Créer `plugins/paved-road/` : routeur + cinq fichiers d'étape (dont la table « quelle preuve pour quel critère », le gabarit de rétro, le gabarit de description de PR), `gap-hunter.md`, déplacer `design-coherence.md` (avec `tools:`) et `skills/smoke` ; `make claude` ; `.dockerignore` | markdown, Makefile | 6 |
| 8 | Remplacer `.github/pull_request_template.md` par le gabarit du parcours | markdown | — |
| 9 | `.claude/rules/` : ligne « Vérifié par » partout ; `paths:` sur `sql.md`, `api.md`, `securite.md`, `review.md` ; `tests.md` repris de `main` | markdown | 1 |
| 10 | `CODEOWNERS` : ajouter `Makefile`, `pyproject.toml`, `.githooks/`, `scripts/`, `lib/attestation.py`, `plugins/paved-road/` | texte | 2 |
| 5 bis | `check_test_quality.py` : échec sur assertion affaiblie d'un test préexistant (diff vs base) ; `skip`/`xfail` ajouté sans `# Why:` | Python, ≈ 30 lignes | 1 |
| 5 ter | `verify_content` étendu à `paved-road/<slug>/**` (rétro et relectures, pas seulement attestations) ; corriger le `pipefail` de `ci.yml` avant que « Ce qui devait marcher » soit requis | Python + YAML, ≈ 10 lignes | 1 |
| 11 | Corriger les documents et le schéma (section 13) | markdown | — |
| 12 | **En dernier** : `permissions.deny`, `permissions.allow` (les commandes du parcours, sinon le PM est noyé sous les invites) et règles `Bash` dans `.claude/settings.json` | JSON | 7, 9 |

Ce qui change pour un PM dès le palier 1 : il lance `make claude`, tape `/paved-road:paved-road`, décrit ce qu'il veut, reçoit un contrat et cinq décisions au plus, répond une fois, relance la commande quand l'agent lui dit qu'une étape est franchie, et revient sur la PR : une description en français, une review app à cliquer, un bouton. Entre-temps l'agent ne peut plus éditer les outils avec ses outils d'écriture ni par redirection de sortie, tout ce qui bloquait déjà bloque toujours, et toute PR qui touche une zone critique ou l'outillage demande le consentement d'un owner (non technique), qui va chercher un avis technique s'il le juge nécessaire.

### Palier 2 — outiller ce que le 1 tient à la main

Checks d'antériorité et d'immuabilité de la DoD ; rapports de relecture committés sous `relectures/`, présence vérifiée, rattachés aux empreintes d'arbre ; `verify_content` sur tout `paved-road/<slug>/**`, aligné en CI ; verdict de `smoke.py plan` committé ; `check_protected_paths.py` (annotation en français du changement d'outillage, surligne les affaiblissements de garde-fou ; pas de label, le gate est CODEOWNERS) ; `check_test_quality.py` : `skip`/`xfail` sans `# Why:` ; `scripts/paved_road_pr_body.py` avec compteurs ; bac à sable ; commandes identiques entre critères (avertissement) ; `S608` bloquant après observation ; compteurs par parcours et plafond famille A ; lentilles sur friction (`surgical-changes`, `security-auditor` conditionnelle, `dod-test-fidelity`) ; renommer `docs/paved-road/l0-…l6-…` ; pre-push qui saute après un `advance` réussi.

### Palier 3 — sur incident ou sur coût

Enchaînement automatique des étapes sans relance humaine ; smoke Playwright headless (sans humain présent) ; lentilles restantes ; validation de la DoD par PR brouillon ; case par `DOD-N` à l'approbation ; E2E dans les checks requis ; evals sur `skills/` et `knowledge/` ; maquette cliquable à Align (emprunt Pocock `prototype`, écarté au palier 1 parce que la review app donne déjà au pair quelque chose à cliquer, plus tard dans le parcours) ; **après-merge** : que fait un non-technicien quand une PR mergée casse la prod (le déploiement est auto, Scalingo + `alembic upgrade head`) ? Le parcours s'arrête à la PR par périmètre assumé, mais le rollback — `git revert` ouvert par l'agent, redéploiement, migration inverse — reste à concevoir avant d'ouvrir le parcours à des surfaces sensibles.

---

## 11. Emprunts, et à qui

- **akria-pipeline** : contrats de stage ; un seul écrivain de verdict ; liste noire Bash plutôt que liste blanche (48 faux positifs sur 82 avec la liste blanche) ; rétro de fin de run ; une session par stage. On n'emprunte pas : les 45 vérificateurs TypeScript, le journal JSONL.
- **Pocock** : interview par rounds avec réponse recommandée ; « trouver les faits est le travail de l'agent, décider est celui de l'humain » ; artefacts du point de vue de l'utilisateur, sans chemin ni code ; skills invoqués par l'humain qui orchestrent, skills invoqués par le modèle qui portent la discipline. On n'emprunte pas : `CONTEXT.md` et ADR, le tracker d'issues, les seams confirmés par un humain technique.
- **Superpowers** : brainstorming avant plan, TDD, revue demandée avant merge.

---

## 12. Décisions à valider

### Pour le demandeur (PM, designer) — oui / non, ou un choix

| # | Décision | Conséquence pour toi | Recommandé |
|---|---|---|---|
| A | L'agent transforme les trous qu'il trouve dans le contrat en critères avec une réponse par défaut, au lieu de te poser des questions en plus | au plus cinq décisions (c'est la consigne du skill ; rien ne le compte encore), et tu peux en contester une après coup | oui |
| B | Tu relances toi-même l'agent entre les étapes (une commande), tant que l'enchaînement automatique n'est pas construit | deux ou trois relances par fonctionnalité, pas de décision à prendre à ces moments | oui |
| C | Le smoke (captures d'écran) se fait dans ta session, tu vois ton navigateur suivre le parcours ; en plus, tu peux essayer toi-même sur la review app | une passe de navigateur sous tes yeux quand une interface est touchée ; une URL à cliquer dans chaque PR, sauf pour les fonctionnalités de données (base vide) | oui |
| D | L'agent écrit un court compte rendu à la fin de chaque parcours ; l'équipe les relit périodiquement et convertit une friction récurrente en check — l'agent écrit le code, le cliquet le valide (observation avant d'armer), donc pas besoin de lire le code | rien pour toi au quotidien ; c'est ce qui fait évoluer le dispositif | oui |
| E | Si la PR touche une zone sensible ou l'outillage, ton approbation ne suffit pas : un owner désigné consent aussi, sur un résumé en français de ce qui change. Il n'est pas plus technique que toi ; s'il ne se sent pas de juger, il va chercher quelqu'un de technique | un délai possible sur ces PR-là, jamais sur les autres | oui |

### Pour l'humain technique — avec recommandation

1. Plugin `plugins/paved-road/` chargé par `make claude` ; hooks et `permissions.deny` restent dans `.claude/settings.json`. Recommandé : oui.
2. `reverse-translation` retiré ; `gap-hunter` outillé en sous-agent lecture seule. Recommandé : oui.
3. Aucun pytest dans les hooks Claude Code ; `pre-commit` de `main` garde la suite hermétique au commit ; `advance` et la CI font le reste. Recommandé : oui.
4. Review dans l'état `build`, gates sur `build → prove` ; ordre lentille → corrections → smoke ; rapports committés au palier 2, rattachés aux empreintes d'arbre. Recommandé : oui.
5. Chemins protégés et quatre couches (section 7), `deny` posé en dernier, `pyproject.toml` en couche 4 seulement. Recommandé : oui.
6. Journal de frictions en prose, `retro.md` par parcours. Recommandé : oui.
7. Rebase de la pile sur `main` avant toute PR d'étage, et reprise de la découpe de #181. Recommandé : oui, c'est le premier chantier.
8. Fermer le trou « l'agent pousse après le oui du pair » : `require_last_push_approval` (le dernier push doit être approuvé par un autre) ou `dismiss_stale_reviews_on_push` (tout push retire l'approbation). Prix : une ré-approbation après chaque rebase. Recommandé : `require_last_push_approval`, le moins bruyant.
9. Plancher de couverture : `main` 74,90 % (`pyproject.toml`), pile 71,00 % (`gates.toml`, commentaire : `skills/` ajouté au périmètre, 1262 instructions jamais exécutées). Recommandé : garder 71,00 % en le disant dans le titre de la PR qui le porte.
10. Rules : `paths:` sur `sql.md`, `api.md`, `securite.md`, `review.md` seulement ; `code.md` et `tests.md` toujours chargés. Recommandé : oui.
11. Bypass du ruleset pour un compte (`louije`, mode `pull_request`, donc visible dans une PR) : (a) le retirer, sachant que trois administrateurs gardent de toute façon la main sur le ruleset ; (b) le garder comme sortie de secours tracée, en l'écrivant dans `CONTRIBUTING.md`. Recommandé : (b).
12. Reporter dans le ruleset la restriction de push et l'historique linéaire de la protection classique, puis la supprimer (doublon pour le reste, force-push autorisé). Recommandé : oui.
13. **Tranché : les lentilles bloquent en session, en boucle de fix (principe 4).** La lentille arrête l'agent tant qu'un bloqueur n'est pas traité ; la CI vérifie la présence du rapport à jour ; le pair le lit dans la PR. Boucle sans plafond (une boucle qui ne converge pas s'interrompt à la main et devient une rétro). Vaut pour design-coherence dès maintenant et pour les lentilles de code (sécurité, architecture, qualité) à mesure qu'elles s'ouvrent. Ce qu'on ne fait pas : rejouer le verdict d'un modèle dans un check CI requis, qui clignoterait.

---

## 13. Écarts relevés entre documents et code

À corriger au palier 1 :

- `CONTRIBUTING.md` : lentille après les preuves (étape 6) ; « Ce qui devait marcher » annoncé requis ; « les sept niveaux sont en place » alors que le journal de frictions et `gap-hunter` n'existent pas.
- `l0-definition-of-done.md` : annonce la vérification des bornes sur le nombre de critères, que `verify_dod` ne fait pas ; n'annonce pas celle des placeholders, qu'il fait.
- `l1-attestation.md` renvoie le rejeu CI au « milestone 4 » ; `l2-quality-gates.md` le décrit au présent (il existe). Les deux définissent C et D différemment.
- `.claude/rules/tests.md` sur la pile dit que l'intégration tourne en CI alors que la CI de la pile l'exclut ; `main` a la version juste. Se résout par le rebase.
- `retrait-spec-kit.md` renvoie la revue obligatoire vers `CODEOWNERS`, réglage éteint.
- La DoD réelle `telecharger-rapport-markdown` crédite `gap-hunter`, qui n'existe pas ; elle contient une question technique (découpage des commits) ; deux critères partagent la même commande de preuve.
- Aucun `docs/paved-road/l4-*.md` pour le smoke, que `CONTRIBUTING.md` décrit en place.
- `check_paved_road.py` et `lib/attestation.py` : deux analyseurs de critères, deux exécuteurs.
- ~~**Bug CI**~~ : `check_paved_road.py … | tee "$GITHUB_STEP_SUMMARY"` rendait le code de sortie de `tee`, pas du script — le check aurait été vert quoi qu'il arrive. **Corrigé le 27 août** par `shell: bash` sur le step, qui active `-eo pipefail`. Mesuré : `bash -e -c 'exit 1 | tee /dev/null'` rend 0, la même chose sous `shell: bash` rend 1.
- Le schéma (`design-workflow-schema.html`, case « Ce qui devait marcher ») dit « relance les commandes des attestations… tout écart échoue » : à corriger, le job ne rejoue pas les preuves navigateur ni nightly (4.4). Schéma à reprendre après validation.
- ~~`.claude/agents/design-coherence.md`~~ : sans `tools:`, il héritait de tout, et son frontmatter annonçait encore un « verdict consultatif, jamais bloquant » qui contredisait la décision 13. **Corrigé le 27 août** : `tools: Read, Grep, Glob`, verdict bloquant, écarts préfixés `BLOQUEUR —` ou `Remarque —`. `CONTRIBUTING.md` plaçait par ailleurs la lentille après le smoke : ordre rétabli.
- Le schéma Slack et les notes d'oral décrivent l'état d'avant le 20 août (cinq checks, `require_last_push_approval: true`, bypass `always`, 47 tests jamais lancés, deux lentilles d'Align). À reprendre après validation.

---

## Annexe A — squelette du plugin

`plugins/paved-road/.claude-plugin/plugin.json`

```json
{ "name": "paved-road", "description": "Parcours de développement Autometa : d'un brief en français à une PR jugeable" }
```

`plugins/paved-road/skills/paved-road/SKILL.md` (frontmatter)

```yaml
---
name: paved-road
description: Démarrer ou reprendre un parcours paved road. Lit l'état (make paved-road-status) et ouvre le fichier de l'étape courante.
disable-model-invocation: true
---
```

Corps : « Lance `make paved-road-status`. Selon l'état : `align` → `align.md` ; `build` → `build.md` puis `review.md` ; `prove` → `prove.md` ; toutes les attestations démontrées → `pr.md` ; PR ouverte avec un commentaire de refus (`gh pr view --comments`) → `build.md` puis `review.md`. Réponds au demandeur en français, sans chemin de fichier ni extrait de code. Quand une étape est franchie, dis-le et demande d'ouvrir une nouvelle session. »

`plugins/paved-road/agents/gap-hunter.md` (frontmatter)

```yaml
---
name: gap-hunter
description: Lentille d'Align — pour chaque critère de la definition of done, cherche l'entrée vide, le doublon, la valeur hors limites, l'état initial absent, l'accès concurrent. Rend des critères proposés avec leur réponse par défaut, jamais des questions. Liste ce qu'il a lu.
tools: Read, Grep, Glob
---
```

`design-coherence.md` reçoit le même `tools:` ; le diff lui est fourni par `review.md` dans `/tmp`.

## Annexe B — `permissions.deny` (extrait)

```json
{
  "permissions": {
    "deny": [
      "Edit(/.claude/settings*)", "Edit(/.claude/hooks/**)", "Edit(/.claude/rules/**)", "Edit(/.claude/agents/**)",
      "Edit(/.github/**)", "Edit(/.githooks/**)",
      "Edit(/gates.toml)", "Edit(/Makefile)",
      "Edit(/scripts/check_*.py)", "Edit(/scripts/paved_road_cli.py)", "Edit(/lib/attestation.py)",
      "Edit(/plugins/paved-road/**)",
      "Edit(/paved-road/*/attestations/**)", "Edit(/paved-road/*/journal/**)",
      "Bash(git push --force*)", "Bash(git push -f *)", "Bash(git commit * --no-verify*)", "Bash(git commit -n *)", "Bash(git -c core.hooksPath=*)",
      "Bash(gh * --add-label*)", "Bash(gh * --label*)"
    ],
    "allow": [
      "Bash(make *)", "Bash(uv run --frozen pytest*)", "Bash(uv run --frozen ruff*)",
      "Bash(git add*)", "Bash(git commit*)", "Bash(git status*)", "Bash(git diff*)", "Bash(git log*)",
      "Bash(gh pr create*)", "Bash(gh pr view*)"
    ]
  }
}
```

Les règles `Edit` couvrent aussi les redirections `>`, `>>`, `2>` vers ces chemins ; pas `sed -i` ni `tee`, qui relèvent du bac à sable (palier 2). Le `deny` reste prioritaire sur l'`allow` : `git commit --no-verify` est refusé même si `git commit*` est permis. La liste `allow` évite au PM une invite d'autorisation à chaque commande du parcours ; sans elle, le mode par défaut lui demande de juger `make`, `pytest`, `git` un par un. Pour modifier l'outillage à la main, on lance `claude --setting-sources user`.

---

## 14. Objections survivantes de la relecture adversariale

Quatre relecteurs ont attaqué ce design sur des axes indépendants (modèle de menace, doctrine, adoption, complétude), suivis de quatre vérificateurs qui ont reconfronté chaque objection au dépôt. Voici ce qui a survécu, avec le palier qui le ferme. Les corrections sont déjà reportées dans les sections concernées ; cette table est le mémo de ce qui reste vrai si on ne les applique pas.

### Ce qu'aucun mécanisme ne ferme, et qui tient à une convention ou à un humain

| Objection | Pourquoi elle survit | Ce qui la contient |
|---|---|---|
| Une DoD infidèle au brief passe tous les gates | aucun programme ne peut comparer un contrat en français à un besoin en français | la phrase de brief rattachée à chaque critère (4.1) + le pair qui relit « Ce qui devra marcher » ligne à ligne (4.5). Convention et lecture humaine, pas un gate |
| La pertinence d'une preuve n'est jugée par personne | un test peut passer sans démontrer le bon comportement | l'id du test doit contenir `dod_N` (4.2, 4.4) : ferme le test au hasard, pas le test mal écrit exprès. Résiduel assumé |
| Pour une feature de données, personne ne compare code et intention | l'ancienne lentille consultative ne bloquait rien + pair qui ne lit pas le code + review app vide | résolu (décision 13) : la lentille bloque en boucle de fix, son rapport est lu par le pair dans la PR |

### Ce qu'un palier ferme (corrections reportées)

| Objection | Sévérité | Fermé par |
|---|---|---|
| L'agent pose lui-même le label `break-glass` et lève le seul gate qui vérifie ses preuves | bloquant | `deny` sur `gh --add-label` + check sur l'auteur du label (palier 1, 4.5, §7) |
| Preuves navigateur et nightly rejouées → PR infusionnable dès que le check est requis | bloquant | verdict `démontré (E2E)` / `(nightly)` non rejoué (palier 1, 4.4) |
| Garde de commande contournée par `--collect-only` ou un test sans rapport | bloquant | `--collect-only` interdit, test `dod_N` exigé (palier 1, 4.4) |
| `permissions.deny` sans `allow` noie le PM sous les invites | bloquant | liste `allow` du parcours (palier 1, §7, annexe B) |
| `skills/` non empreinté : réécrire un `SKILL.md` ne périme rien | important | `skills` ajouté aux empreintes (palier 1, 4.4) |
| `retro.md` obligatoire au palier 1 sur dépôt public, non scanné | important | `verify_content` étendu à `paved-road/<slug>/**` (palier 1, 4.3, §8) |
| Le bac à sable du palier 2 bloquerait `advance` | important | `denyWrite` limité à l'outillage, pas aux attestations (§7 couche 2) |
| `design-coherence` sautable sans trace au palier 1 | résolu | boucle de fix bloquante en session dès le palier 1 ; présence gated en CI au palier 2 (4.3, décision 13) |
| Affaiblir une assertion d'un test existant pour rester vert | important | échec de `check_test_quality` sur assertion affaiblie (palier 1, 4.2) |
| Bug CI : `tee` sans `pipefail` rend le check toujours vert | important | `pipefail` avant que le check soit requis (palier 1, §13) |
| Révision d'une DoD infaisable en plein Build : impasse | important | procédure de révision + verbe `revise` (§9, palier 2) |
| Rebase concurrent : re-`prove` et re-smoke non annoncés | important | cascade décrite, sériation des parcours (4.5) |

### Ce qui reste à concevoir hors de ce document

| Trou | Statut |
|---|---|
| Rollback d'une PR mergée qui casse la prod | hors périmètre assumé ; à concevoir avant d'ouvrir à des surfaces sensibles (palier 3) |
| Mise à jour des postes PM et versionnement du plugin | omission de checklist ; une ligne au chantier 3 bis |
| Coût en tokens d'un run (le smoke seul : centaines de milliers) | jamais chiffré ; `lib/paved_road.py` ne voit pas les sessions du parcours. Exiger `/cost` dans `retro.md`, mesurer avant le palier 3 |
| Lecture périodique du journal de frictions | portée par l'équipe (non technique) : elle convertit une friction en check via le parcours, le cliquet valide en observation avant d'armer (§8). Reste à fixer une cadence et à la nommer dans `CONTRIBUTING.md`, sinon le cliquet ralentit faute de rythme — plus faute de personne |
| Pool de relecteurs réel = 2 (l'auteur de la pile est titulaire) | charge du palier 1 non chiffrée ; l'étage 04 fait 75 fichiers. Risque de goulot |
| Build en session interactive : le PM voit défiler des tests rouges pendant des heures, présence requise | pas de signal de progression ; à traiter avec l'enchaînement automatique (palier 3) |
| Correction d'un code critique sous relecture 100 % non technique | risque assumé : aucun owner ne peut certifier qu'un changement du TaskRunner ou d'une migration est correct. La garantie tient au déterministe (tests, rejeu, lentilles bloquantes) ; le reste est un angle mort, borné en rendant ces changements rares et consentis (§7). Le combler demande d'appeler quelqu'un de technique, pas un rôle permanent |


---

## 15. Décisions et corrections du 27 août

### Décisions prises

| # | Sujet | Tranché |
|---|---|---|
| D1 | **pip-audit** | reste un gate de la CI de PR, en `continue-on-error: true`. Le workflow nightly `dependencies.yml` **n'est pas du palier 1** : il attend le palier 2, où il aura un destinataire (issue ouverte, ou canal d'alerte). Mesuré sur 117 runs (20 juillet → 27 août) : `Security` est le job le plus fragile du dépôt, 12 échecs, dont **11 dus à pip-audit**. Un check requis qui rougit une PR sur dix pour une raison sans rapport avec elle apprend à l'équipe à ignorer le rouge ; un nightly que personne ne lit ne vaut pas mieux. Le non-bloquant garde le signal sans immobiliser |
| D2 | **job E2E** | reste sur le runner local (`E2E_BASE_URL: http://127.0.0.1:8000`). Le branchement sur l'URL de review app publiée par #191 est reporté au palier 2 : `REVIEW_APP_HTPASSWD` n'existe ni dans les secrets du dépôt ni dans ceux de l'organisation, donc le second mode d'entrée de `bin/with_review_app_auth.sh` ne peut pas fonctionner aujourd'hui. La limite est écrite dans `docs/paved-road/l3-e2e.md` |
| D3 | **ce document** | versé dans `docs/plans/` plutôt que gardé hors dépôt. Le design de juillet (`2026-07-28`, 1331 lignes) n'est pas versé : ses « sept niveaux » sont déjà documentés un par un par `docs/paved-road/l0-…l6-…`, et son exemple de DoD est périmé par la DoD réelle de `telecharger-rapport-markdown` |
| D4 | **titulaires `CODEOWNERS`** | `@louije`, `@Annaelle24`, `@cdarnispro` — en pratique le duo Louis-Jean + Annaelle. Écart assumé avec le principe 9 : Louis-Jean tient le rôle de pair bien qu'il soit le développeur principal du dépôt. Au palier 1, le pair d'Annaelle sera donc technique |

### Corrections déjà portées

- `check_required_checks.py` lit le ruleset et échoue sur API illisible (chantier 4, 24 tests).
- `ci.yml` : `shell: bash` sur « Ce qui devait marcher » (chantier 5 ter, partie `pipefail`).
- `design-coherence.md` : `tools:` et verdict bloquant ; `CONTRIBUTING.md` : lentille avant smoke.

### Un piège trouvé en chemin, à corriger au rebase de l'étage 03

`tests/conftest.py` appelle `load_dotenv()` sans argument. python-dotenv **remonte alors
l'arborescence** jusqu'à trouver un `.env` : dans un worktree qui n'a pas le sien, il sort du dépôt
et prend celui du répertoire personnel. Mesuré : les tests de la pile visaient
`postgresql://…@localhost:5556/tech_test`, la base d'un autre projet. Le commentaire du code
annonce l'inverse de ce qu'il fait. Correctif : `load_dotenv(Path(__file__).parent.parent / ".env")`.

Sur `main` le problème est masqué — `make test` force `DATABASE_URL=` et python-dotenv ne remplace
pas une variable définie — mais un `pytest` lancé hors cible Makefile le rouvre.
