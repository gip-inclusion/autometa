# Vérifier la qualité visuelle des tableaux de bord générés

## Ce que je veux

Vérifier automatiquement la qualité visuelle des tableaux de bord que l'assistant génère, avant que
quelqu'un les ouvre : qu'ils s'affichent, que leurs graphiques ne soient pas vides, qu'aucune erreur
ne traîne à l'écran. L'assistant ne doit plus donner l'adresse d'un tableau de bord cassé sans le
dire.

## Ce qui devra marcher

DOD-1 — [du brief : « vérifier automatiquement la qualité visuelle »] Quand je fais vérifier un
  tableau de bord sain, il est affiché dans un vrai navigateur, ses graphiques sont comptés, une
  capture d'écran de la page est produite, et le verdict est positif.

DOD-2 — [du brief : « erreurs JS, requêtes en échec »] Quand le tableau de bord déclenche une erreur
  JavaScript, ou qu'un fichier dont il dépend (script, style, données) ne se charge pas, le verdict
  est négatif et nomme l'erreur ou le fichier. Une police ou une image manquante ne donne qu'un
  avertissement.

DOD-3 — [du brief : « graphiques vides ou absents »] Quand un graphique s'affiche vide, sans taille,
  ou avec une série sans aucune valeur, ou quand il y a moins de graphiques que le nombre attendu,
  le verdict est négatif et nomme le graphique concerné.

DOD-4 — [du brief : « mise en page cassée, valeurs NaN »] Quand la page déborde en largeur, n'affiche
  aucun texte, affiche un message d'erreur, ou montre « NaN », « undefined » ou « [object Object] »,
  le verdict est négatif et dit lequel de ces défauts il a vu.

DOD-5 — [du brief : « renvoie un verdict »] Chaque vérification rend un verdict, réussi ou échoué,
  avec la liste des défauts trouvés, chacun marqué erreur ou avertissement ; seules les erreurs font
  échouer. Quand la vérification ne peut pas avoir lieu (tableau de bord introuvable, navigateur
  absent), elle le dit au lieu de rendre un verdict.

DOD-6 — [du brief : « étape finale de la création et de la modification d'un tableau de bord »]
  Après avoir créé ou modifié un tableau de bord, l'assistant le fait vérifier avant d'en donner
  l'adresse, et corrige jusqu'à obtenir un verdict positif. S'il reste une erreur qu'il ne sait pas
  corriger, il donne quand même l'adresse mais annonce que le tableau de bord n'a pas passé la
  vérification, avec la liste des défauts restants.

DOD-7 — [proposé par la chasse aux trous, valeur par défaut retenue] Vérifier un tableau de bord ne
  compte aucune visite dans les statistiques de fréquentation du site.

DOD-8 — [proposé par la chasse aux trous, valeur par défaut retenue] Quand un tableau de bord prend
  ses données en direct auprès de l'application et qu'on le vérifie par son nom, ces demandes sont
  signalées en avertissement comme non vérifiables hors de l'application ; si ses graphiques restent
  vides pour cette raison, le verdict est négatif. Pour le vérifier en entier, on le vérifie à
  l'adresse de l'application lancée localement.
  Révision 2026-09-18 — « en entier » est faux, relevé par la relecture de cohérence : même à
  l'adresse de l'application lancée localement, une demande de données que l'application refuse
  n'est qu'un avertissement ; seuls les graphiques restés vides ou le message d'erreur du tableau
  de bord font alors échouer. À revalider par Alexis.

DOD-9 — [proposé par la chasse aux trous, valeur par défaut retenue] Un tableau de bord fait
  uniquement de chiffres clés, sans graphique, et dont on n'attend aucun graphique, reçoit un
  verdict positif, avec l'avertissement « aucun graphique détecté ».

DOD-10 — [proposé par la chasse aux trous, valeur par défaut retenue] Une table de chiffres très large qui
  défile dans son propre cadre n'est pas un défaut : seul le défilement horizontal de la page
  entière fait échouer.

## Sources lues

- `lib/viz_quality.py`, `skills/verify_dashboard/`, `tests/test_viz_quality.py`,
  `browser/test_verify_dashboard.py` — **R1** : la surface n'existe pas « à moitié », elle existe
  **en entier** : le code et ses tests ont été écrits et committés avant ce contrat (voir « Questions
  ouvertes »). Les critères décrivent le comportement que le brief demandait, relu dans le code et
  non déduit de lui.
- `skills/create_dashboard/SKILL.md`, `skills/update_dashboard/SKILL.md`, `AGENT.md` — **R1** : le
  seul endroit où « étape finale » peut s'écrire. Aucun code ne marque la fin de génération d'un
  tableau de bord : c'est l'agent qui écrit les fichiers, donc `DOD-6` repose sur une consigne.
- `lib/dashboard_api.py` — **R4** : la vérification n'importe pas la façade et ne la modifie pas ;
  aucun tableau de bord de production n'en dépend.
- `docs/interactive-dashboards.md` — **R5** : conventions du gabarit (`#generated-at`, `#error`,
  `data.json`) sur lesquelles `DOD-4` s'appuie.

Aucun critère ne porte de chiffre : **R2** ne se déclenche pas. Aucun terme IAE : **R3** non plus.

## Questions ouvertes

1. **Le contrat est écrit après le code.** La fonctionnalité a été construite et committée (PR
   ouverte) avant que ce contrat existe ; il est ajouté a posteriori pour mettre la PR au format du
   parcours. Le parcours le refuse, et c'est à Alexis de décider s'il accepte cette PR ainsi, en
   allant chercher un avis technique comme le demande le parcours.
2. **`DOD-6` n'a pas de preuve automatique possible.** Il repose sur une consigne donnée à
   l'assistant ; aucun programme ne sait dire si l'assistant la suit. Il restera « non démontré »
   tant qu'on ne l'a pas constaté sur une vraie génération de tableau de bord.

### Décisions soumises à Alexis

Ne rien répondre, c'est accepter le défaut. Les défauts 3 à 5 laissent le comportement tel qu'il
est dans cette PR et renvoient l'amélioration à un parcours suivant : cette PR est une mise au
format, pas une réécriture.

**Décision 1 — Accepter une PR dont le contrat est écrit après le code.**
Par défaut : oui, en demandant à un pair technique de relire le code avant d'approuver, comme le
parcours l'exige pour du code daté avant son contrat.
Autrement : repartir de zéro dans un nouveau parcours, contrat d'abord ; la fonctionnalité est
retardée d'autant.

**Décision 2 — Un tableau de bord qui reste en échec est-il livré ?**
Par défaut : oui, mais l'assistant annonce qu'il n'a pas passé la vérification et liste les défauts
(`DOD-6`). Tu reçois toujours ton tableau de bord, et tu sais ce qui cloche.
Autrement : l'assistant refuse de donner l'adresse tant que le verdict est négatif ; aucun tableau
de bord cassé ne sort, mais une erreur qu'il ne sait pas corriger te laisse sans rien.

**Décision 3 — L'assistant oublie de dire combien de graphiques il attend.**
Par défaut : la vérification ne compte pas, et un tableau de bord dont tous les graphiques ont
disparu ne reçoit qu'un avertissement ; la consigne oblige l'assistant à toujours donner ce nombre.
Autrement : sans nombre donné, exiger au moins un graphique ; un tableau de bord fait uniquement de
chiffres clés devrait alors le déclarer (`DOD-9` changerait).

**Décision 4 — Une page trop lente à charger.**
Par défaut : la vérification dit qu'elle n'a pas pu avoir lieu, en suggérant à tort que le
navigateur manque.
Autrement : un parcours suivant fait nommer la lenteur (« page non chargée en 30 s ») et la
compte comme un échec du tableau de bord.

**Décision 5 — Les graphiques cachés au chargement (un onglet inactif).**
Par défaut : ils ne sont pas vérifiés, et le verdict ne le dit pas ; un graphique cassé dans un
second onglet passe inaperçu.
Autrement : un parcours suivant fait annoncer leur nombre dans le verdict (« 2 graphiques masqués
non vérifiés »).

## Validation

Validé par clawdio, par délégation d'Alexis Akinyemi, le 2026-09-18 — relecture humaine des
critères encore à faire : ni Alexis ni un pair ne les a lus à cette date.
