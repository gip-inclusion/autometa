# Vérifier la qualité visuelle d'un tableau de bord avant d'en partager le lien

## Ce que je veux

Quand l'agent crée ou modifie un tableau de bord, il le regarde comme le ferait un utilisateur avant
de donner le lien : la page s'affiche-t-elle sans erreur, les graphiques sont-ils dessinés, aucune
valeur cassée n'apparaît-elle ? Il obtient un verdict clair, réussi ou échoué, avec la liste des
problèmes, et corrige avant de partager.

## Ce qui devra marcher

DOD-1 — [du brief : « rendu headless », « verdict structuré réussi / échoué »] Quand l'agent lance la
  vérification sur un tableau de bord sain, la page est affichée dans un navigateur sans écran et
  le verdict est « réussi », avec une liste de problèmes vide — sans qu'Autometa ait besoin d'être
  démarré.

DOD-2 — [du brief : « erreurs JS / console »] Quand le code du tableau de bord plante ou écrit une
  erreur dans la console du navigateur, le verdict est « échoué » et le problème cite le message
  d'erreur.

DOD-3 — [du brief : « requêtes de ressources en échec »] Quand un fichier dont le tableau de bord a
  besoin pour fonctionner (ses données, un script, une feuille de style) ne se charge pas, le
  verdict est « échoué » et le problème nomme ce fichier.

DOD-4 — [du brief : « graphiques vides ou absents »] Quand un graphique est affiché sans aucun tracé,
  ou quand la page montre moins de graphiques que l'agent n'en attend, le verdict est « échoué » et
  le problème le dit.

DOD-5 — [du brief : « NaN / undefined »] Quand la page affiche « NaN », « undefined », « null » ou
  « [object Object] » à la place d'une valeur, le verdict est « échoué » et le problème cite la
  valeur cassée.

DOD-6 — [du brief : « mise en page cassée »] Quand le contenu déborde horizontalement sur un écran
  d'ordinateur de 1280 pixels de large, ou quand la page n'affiche aucun texte, le verdict est
  « échoué ».

DOD-7 — [du brief : « dernière étape de la création / modification », « avant que son URL soit
  partagée »] Les consignes de création et de modification d'un tableau de bord demandent à l'agent,
  une fois les fichiers du tableau de bord écrits (et ses données générées une première fois s'il
  en a), de lancer la vérification ; tant que le verdict est « échoué », de corriger puis relancer,
  trois tentatives au plus ; puis de ne donner le lien qu'après un verdict « réussi », ou en
  listant à l'utilisateur les problèmes qu'il n'a pas su corriger. Une modification qui ne touche
  que le titre, les étiquettes ou l'archivage ne déclenche pas de vérification.

DOD-8 — [du brief : « requêtes de ressources en échec »] Le script de mesure d'audience du gabarit
  n'est jamais chargé pendant la vérification : elle ne compte aucune fausse visite, et l'absence de
  ce script n'est pas un problème.

DOD-9 — [du brief : « requêtes de ressources en échec »] Quand le tableau de bord lit ses données en
  direct auprès d'Autometa, ces lectures, impossibles hors de l'application, ne font pas échouer le
  verdict : elles sortent en avertissement « données en direct non vérifiées ».

DOD-10 — [du brief : « mise en page cassée »] Quand la page affiche son bloc d'erreur avec un texte,
  ou montre encore « Chargement… » une fois la page chargée, le verdict est « échoué » et le problème
  cite ce texte.

DOD-11 — [du brief : « tableau de bord généré »] Quand le tableau de bord n'a pas de page d'accueil,
  le verdict est « échoué » avec le problème « index.html introuvable », sans que l'outil plante.

DOD-12 — [du brief : « rendu headless »] Quand la page n'a pas fini de charger au bout de 30
  secondes, le verdict est « échoué » avec le problème « délai dépassé », et l'agent obtient un
  verdict au lieu d'attendre indéfiniment.

DOD-13 — [du brief : « graphiques vides ou absents », « NaN / undefined »] La vérification ne crie
  pas au loup : sans nombre de graphiques attendu, aucun minimum n'est exigé (un tableau de bord
  fait de tableaux passe) ; un graphique caché au premier affichage, dans un onglet inactif, n'est
  pas jugé vide ; « NaN », « undefined », « null » ne sont repérés que comme mots entiers du texte
  visible, et une même valeur cassée répétée n'est signalée qu'une fois, avec son nombre
  d'occurrences.

DOD-14 — [du brief : « avant que son URL soit partagée »] La vérification fonctionne là où l'agent
  crée les tableaux de bord en production, pas seulement sur un poste de développement.

## Sources lues

- `skills/create_dashboard/`, `skills/update_dashboard/`, `lib/dashboards.py` — **R1** : les deux
  scripts ne font que réserver le dossier et écrire les métadonnées ; ils tournent **avant** que
  l'agent écrive le HTML. La vérification ne peut donc pas vivre dans ces scripts : elle est une
  étape que l'agent enchaîne après avoir écrit les fichiers, d'où la forme de `DOD-7`.
- `docs/interactive-dashboards.md`, `docs/dashboard-template/` — **R1** : structure imposée
  (`index.html`, `app.js`, `style.css`, `data.json`), Chart.js ou D3 / Observable Plot depuis un
  CDN, bloc `#error` pour les messages d'erreur, pied de page `#generated-at`, tag manager Matomo en
  dur dans le gabarit.
- `web/app.py:serve_interactive`, `web/config.py` — **R1** : l'application sert un tableau de bord
  sous `/interactive/{slug}/` et les ressources partagées sous `/common/`.
- `browser/conftest.py`, `.github/workflows/e2e.yml`, `.github/workflows/ci.yml`, `Makefile` — **R1** :
  Chromium n'est installé que dans le couloir de navigateur ; le couloir unitaire n'en a pas.
- `lib/dashboard_api.py` — **R4** : la vérification ne l'importe ni ne le modifie ; aucun tableau de
  bord de production n'est touché.
- `docs/plans/2026-08-22-paved-road-workflow.md`, `docs/paved-road/l0-definition-of-done.md` — **R5**.
- Branche `feat/viz-quality-playwright` (PR #228) — consultée comme référence de ce qu'un
  navigateur sait mesurer, pas comme contrat.
- `Dockerfile`, `pyproject.toml` — **R1** : l'image de production installe les dépendances sans le
  groupe de développement ; le navigateur de Playwright n'y est pas. D'où `DOD-14`.

Chiffres — **R2** :
- `DOD-6`, 1280 pixels : largeur par défaut d'une page Playwright hors émulation mobile (1280×720),
  et largeur retenue par la PR #228.
- `DOD-12`, 30 secondes : délai de navigation par défaut de Playwright.
- `DOD-7`, trois tentatives : pas de mesure disponible, valeur par défaut proposée par la lentille
  `gap-hunter` et retenue comme décision 5 ci-dessous.

Aucune source de données métier n'a été consultée : la demande spécifie un outil d'Autometa, pas une
analyse.

## Questions ouvertes

Aucune.

## Décisions soumises

1. **Un verdict « échoué » informe, il ne bloque pas.** Par défaut : l'agent corrige et relance ; s'il
   n'y arrive pas, il donne le lien en listant les problèmes. Autrement : refuser de donner ou de
   publier le lien tant que le verdict est « échoué » — plus sûr, mais un tableau de bord dont un
   CDN tombe devient inlivrable.
2. **Données en direct** (`DOD-9`). Par défaut : avertissement. Autrement : échec, et ces tableaux de
   bord ne pourraient jamais obtenir « réussi ».
3. **Largeur d'écran** (`DOD-6`). Par défaut : ordinateur, 1280 pixels. Autrement : vérifier aussi en
   largeur de téléphone — double le temps de vérification et fait échouer des tableaux de bord
   pensés pour l'ordinateur.
4. **Navigateur en production** (`DOD-14`). Par défaut : l'image de production embarque un navigateur
   sans écran, qui l'alourdit. Autrement : vérification réservée au poste de développement — l'agent
   de production donnerait ses liens sans avoir rien regardé, ce qui vide la demande.
5. **Nombre de tentatives** (`DOD-7`). Par défaut : trois. Autrement : sans limite, au risque d'une
   boucle quand la panne n'est pas dans le tableau de bord.

`DOD-8` à `DOD-14` viennent de la lentille `gap-hunter` (sauf `DOD-14`, trouvé à la lecture du
`Dockerfile`) et sont proposés avec leur valeur par défaut.

## Validation

Validé par Alexis Akinyemi le 2026-09-18, par délégation : le brief confie à l'agent le rôle de
demandeur et l'autorise à trancher les décisions avec leurs valeurs par défaut. Les cinq défauts
ci-dessus sont retenus sans modification. Cette validation est auto-déclarative (voir « Dette
assumée » de L0) : le demandeur la confirmera ou la contestera à la lecture de la PR.
