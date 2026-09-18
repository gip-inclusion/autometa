## Ce que je voulais

Vérifier automatiquement la qualité visuelle des tableaux de bord que l'assistant génère, avant que
quelqu'un les ouvre : qu'ils s'affichent, que leurs graphiques ne soient pas vides, qu'aucune erreur
ne traîne à l'écran.

> ⚠️ **Contrat écrit après le code.** Le code de cette PR a été écrit et poussé le 2026-09-18 à
> 12 h 15, et le contrat (definition of done) seulement ensuite, pour mettre la PR au format du
> parcours. Le parcours refuse de sceller ce contrat, et c'est normal : rien ne distingue ici un
> accord passé d'avance d'une description écrite après coup. **Ne pas approuver sans un avis
> technique sur le code.**

## Ce qui devait marcher

Sortie de `make paved-road-status` (état `align`, refusé — voir plus bas) :

| Critère | Ce qui devait marcher | Verdict | Preuve |
|---|---|---|---|
| DOD-1 | Un tableau de bord sain est affiché dans un vrai navigateur, ses graphiques sont comptés, une capture est produite, le verdict est positif. | non démontré | — |
| DOD-2 | Une erreur JavaScript, ou un script, style ou fichier de données qui ne se charge pas, donne un verdict négatif qui les nomme ; police ou image manquante : avertissement. | non démontré | — |
| DOD-3 | Un graphique vide, sans taille, avec une série sans valeur, ou moins de graphiques qu'attendu : verdict négatif, graphique nommé. | non démontré | — |
| DOD-4 | Page qui déborde, sans texte, avec un message d'erreur, ou montrant « NaN », « undefined », « [object Object] » : verdict négatif, défaut nommé. | non démontré | — |
| DOD-5 | Chaque vérification rend un verdict et la liste des défauts, marqués erreur ou avertissement ; si elle ne peut pas avoir lieu, elle le dit. | non démontré | — |
| DOD-6 | Après création ou modification d'un tableau de bord, l'assistant le fait vérifier avant d'en donner l'adresse, corrige, et annonce les défauts qu'il n'a pas su corriger. | non démontré | — |
| DOD-7 | Vérifier un tableau de bord ne compte aucune visite dans les statistiques du site. | non démontré | — |
| DOD-8 | Un tableau de bord à données en direct, vérifié par son nom : demandes signalées en avertissement, verdict négatif si ses graphiques restent vides (révisé le 2026-09-18). | non démontré | — |
| DOD-9 | Un tableau de bord de chiffres clés, sans graphique attendu : verdict positif avec l'avertissement « aucun graphique détecté ». | non démontré | — |
| DOD-10 | Une table très large qui défile dans son cadre n'est pas un défaut ; seul le débordement de la page entière fait échouer. | non démontré | — |

Contrat complet : `paved-road/viz-quality-playwright/definition-of-done.md`.

## Ce qui n'a pas été démontré

**Les dix critères, au sens du parcours** — aucune attestation n'a pu être produite, pour deux
raisons qui tiennent toutes les deux au fait que le code précède le contrat :

1. **Le contrat n'est pas scellé.** Le contrôle d'antériorité refuse : du code est committé avant le
   contrat. La seule « réparation » serait de réécrire l'historique d'une branche déjà poussée, ce
   qui est interdit et viderait ce contrôle de son sens. Le parcours reste donc à l'état `align`.
2. **Aucune preuve « rouge puis vert » n'est honnêtement possible.** Le parcours exige d'avoir vu
   chaque test échouer avant que le code existe ; les tests passent déjà. Renommer les tests
   existants après chaque critère ne créerait pas ce rouge — on l'aurait fabriqué.

**Ce qui existe en revanche, hors mécanisme d'attestation**, et que le pair peut rejouer
(`uv run --frozen pytest tests/test_viz_quality.py` → 25 passés ; `uv run --frozen pytest
browser/test_verify_dashboard.py` → 2 passés, joués localement le 2026-09-18 sur `8c9c96d`, et en
CI sur la PR) :

| Critère | Tests existants qui l'exercent |
|---|---|
| DOD-1 | navigateur : TDB sain → verdict positif, 2 graphiques comptés, capture non vide |
| DOD-2 | unitaire : erreurs console / page / réseau par sévérité ; navigateur : `donnees.json` en 404 nommé |
| DOD-3 | unitaire : graphique de taille nulle, vide, Chart.js cassé, graphique manquant ; navigateur : canvas vide nommé |
| DOD-4 | unitaire : débordement, NaN, bandeau d'erreur, page vide ; navigateur : NaN et débordement nommés |
| DOD-5 | unitaire : verdict positif malgré des avertissements, codes de sortie 0 / 1 / 2 (TDB introuvable, navigateur absent) |
| DOD-6 | **aucun** — consigne donnée à l'assistant dans ses instructions ; aucun programme ne sait vérifier qu'il la suit |
| DOD-7 | **partiel** — unitaire : la requête vers l'outil de statistiques, bloquée, n'est pas comptée comme défaut ; le blocage lui-même n'est exercé par aucun test |
| DOD-8 | unitaire : un refus de `/api/query` est un avertissement « non vérifiable hors application servie » |
| DOD-9 | unitaire : aucun graphique et aucun attendu → avertissement seul |
| DOD-10 | **partiel** — le débordement de page est testé ; la table qui défile dans son cadre, non |

**Limites connues, non couvertes par le contrat** (relevées par les relectures, laissées en
décisions à Alexis ou pour un parcours suivant) :

- une page qui met plus de 30 s à charger est annoncée « audit impossible, navigateur absent ? » —
  diagnostic trompeur (Décision 4) ;
- les graphiques cachés au chargement (onglet inactif) ne sont pas vérifiés, et le verdict ne le dit
  pas (Décision 5) ;
- si l'assistant oublie de donner le nombre de graphiques attendus, un tableau de bord dont tous les
  graphiques ont disparu ne reçoit qu'un avertissement (Décision 3) ;
- l'examen des séries vides ne vaut que pour Chart.js ; un Chart.js sans aucune série passe ;
- une vérification par adresse qui tombe sur la page de connexion n'est pas reconnue comme telle ;
- deux vérifications simultanées du même tableau de bord écrivent la même capture.

Smoke : « Interface inchangée : rien à signaler au relecteur au sujet du smoke. »

## Pour juger sans lire le code

- **Review app** : sans objet. Une review app part d'une base vide et ce contrôle ne s'affiche nulle
  part dans l'application : il tourne quand l'assistant génère un tableau de bord. Il n'y aura rien
  à cliquer — ce n'est pas un signe de panne.
- **Captures du smoke** : aucune — interface inchangée.
- **Relecture `design-coherence`** (`paved-road/viz-quality-playwright/design-coherence.md`) : un
  bloqueur à la première passe — le contrat promettait qu'un tableau de bord cassé ne serait jamais
  livré, alors que la consigne le fait livrer avec ses défauts annoncés. Corrigé **dans le contrat**
  (le code fait ce qui était voulu : informer sans bloquer), et le choix bloquer / informer est
  soumis à Alexis. Seconde passe : aucun bloqueur ; une promesse trop large de `DOD-8` corrigée par
  une révision datée.
- **Chasse aux trous** (`paved-road/viz-quality-playwright/gap-hunter.md`) : trois critères ajoutés
  (`DOD-8` à `DOD-10`), cinq décisions soumises.
- **Décisions en attente d'Alexis** (ne rien répondre = accepter le défaut) : 1. accepter une PR au
  contrat écrit après le code — défaut : oui, avec relecture technique ; 2. livrer un tableau de bord
  qui reste en échec — défaut : oui, en l'annonçant ; 3. nombre de graphiques oublié — défaut :
  inchangé ; 4. page lente — défaut : inchangé ; 5. graphiques cachés — défaut : inchangé.
- **Validation du contrat** : faite par l'agent orchestrateur par délégation, **pas encore lue par
  Alexis ni par un pair**.
- **Premier commit de code** : 2026-09-18 12:15 (`735cafe`) · **premier commit du contrat** :
  2026-09-18, après le code (`a01888f`).

> Règle de lecture pour le pair : du code daté **avant** le contrat, on ne signe pas — on va
> d'abord chercher un avis technique.

## Ce que cette PR change dans l'outillage

Aucun garde-fou n'est affaibli : aucun seuil, test, contrôle ni hook du parcours n'a été modifié.

- **Zone critique — `Dockerfile`** : l'image de production installe désormais le navigateur
  Chromium sans interface, dont la vérification a besoin. Ce changement touche une zone critique et
  nécessite une relecture humaine, et le consentement d'un owner.
- `pyproject.toml` / `uv.lock` : Playwright devient une dépendance de l'application, et plus
  seulement des tests.
- `scripts/doctor.py` : le diagnostic de poste signale l'absence du navigateur avec la commande qui
  l'installe.

---

<sub>Parcours et attendus : `CONTRIBUTING.md`. Conception : `docs/plans/2026-08-22-paved-road-workflow.md`.</sub>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
