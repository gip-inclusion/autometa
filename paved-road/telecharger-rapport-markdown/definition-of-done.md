# Télécharger un rapport en Markdown

## Ce que je veux

Depuis la page d'un rapport, récupérer le rapport sous forme de fichier, pour l'envoyer par mail ou
le ranger dans un dossier — sans copier-coller depuis le navigateur.

## Ce qui devra marcher

DOD-1 — Quand je clique sur « Télécharger en Markdown » depuis un rapport, alors un fichier se
  télécharge, au lieu de s'afficher dans un onglet.

DOD-2 — Le fichier téléchargé porte le titre du rapport dans son nom, et l'extension `.md`.

DOD-3 — Le fichier contient le texte du rapport tel qu'il a été écrit, sans rien retirer ni ajouter.

DOD-4 — Quand le titre du rapport ne donne aucun nom de fichier lisible (titre vide, ou uniquement
  des caractères spéciaux), alors le fichier s'appelle `rapport-<numéro du rapport>.md`.

DOD-5 — Les liens déjà partagés vers la « version exportable » d'un rapport continuent de mener à ce
  rapport.

## Sources lues

- `web/routes/reports.py`, `web/templates/rapports.html`, `tests/test_rapports.py` — **R1** : la
  surface existe déjà à moitié. Le bouton « Version exportable » ouvre `/rapports/<id>.txt` dans un
  onglet, en `text/plain`, sans en-tête de téléchargement : le navigateur affiche le texte, et
  l'enregistrer donne un fichier nommé d'après le numéro du rapport. C'est ce demi-état qui rend
  `DOD-1`, `DOD-2` et `DOD-5` nécessaires — sans cette lecture, la fonctionnalité aurait été
  déclarée faite.
- `web/deps.py:get_current_user`, `scripts/check_route_auth.py`, `gates.toml` — **R1** : une route
  neuve naît sans protection et le guardrail la refuse. La route de téléchargement porte donc une
  dépendance d'authentification, et la baseline de `gates.toml` n'est pas étendue.

Aucun critère ne porte de chiffre : **R2** ne se déclenche pas.

Aucune source de données métier (Zendesk, Metabase, Matomo, RPE) n'a été consultée : elles servent à
répondre à une question d'analyse, pas à spécifier une fonctionnalité d'Autometa.

## Questions ouvertes

Aucune.

## Validation

Validé par cdarnis.pro@gmail.com le 2026-08-18.

Quatre décisions soumises, quatre défauts retenus sans modification : nom du fichier tiré du titre du
rapport, contenu conservé intégralement en-tête technique comprise, bouton renommé « Télécharger en
Markdown ». La quatrième portait sur le découpage des commits, hors contrat.

`DOD-5` n'a pas été soumis comme question : la lentille `gap-hunter` l'a trouvé au-delà du budget de
décisions, il est donc proposé avec sa valeur par défaut.
