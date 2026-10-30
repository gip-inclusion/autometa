# Rédiger un ticket du backlog depuis le chat d'autometa

## Ce que je veux

Dans le chat d'autometa, je colle des notes, un vocal transcrit, un fil Slack ou un lien Figma,
et je demande un ticket. L'agent me propose un ticket court du Backlog unifié : un titre, un
paragraphe d'ouverture marqué `:autometa:`, puis Périmètre, Attendu, À trancher, Pistes
techniques évoquées et Sources. Il recommande l'équipe, le statut, le type, l'épic et la
propriété où m'inscrire, et me pose au plus trois questions. Il lit la maquette Figma. Il ne crée
le ticket qu'après mon accord.

## Ce qui devra marcher

DOD-1 — Un lien Figma vers un cadre donne, pour chaque cadre, son nom, ses textes visibles et une
image que l'agent peut regarder ; un lien sans cadre précis n'est pas lu, et l'agent le dit.

DOD-2 — Le contexte des équipes (équipes produit actives, épics actifs, titres de tickets récents)
est rangé chaque jour, et relu dans Notion s'il a plus d'un jour.

DOD-3 — Les tickets proches d'un titre proposé sont retrouvés et classés ; l'auteur est inscrit dans
`POM`, `UX`, `Développeurs` ou `Contributeurs` selon son rôle et l'équipe destinataire.

DOD-4 — Le ticket créé porte le titre, le corps, l'équipe, le statut, le type, l'épic et la
maquette ; jamais Priorité, Période ni Estimation ; un statut d'avancement de développement
(Ce sprint, En cours, En prod…) est refusé.

DOD-5 — Rien n'est écrit dans Notion sans `--go` : sans lui, le script montre seulement ce qui
serait créé.

## Décisions (validées le 2026-10-30)

1. Le marqueur `:autometa:` devient l'emoji personnalisé de l'espace. Essai du 2026-10-30 dans une
   page bac à sable : l'API accepte la mention `custom_emoji` dans un texte.
2. Âge maximal du contexte rangé avant relecture dans Notion : un jour.
3. Un ticket proche est signalé quand son titre partage au moins la moitié des mots-clés du titre
   proposé, et au moins deux ; l'agent ne montre que ceux qu'il juge vraiment proches. Mesuré le
   2026-10-30 sur 150 titres du backlog : 37 % ont au moins un candidat, contre 66 % avec « deux
   mots en commun ».
   Révision 2026-10-30 — après la relecture du code (plus de plafond à 100 résultats, élisions
   détachées, comparaison au début des mots, préfixes entre crochets ignorés), la règle est
   inchangée ; nouvelle mesure, apostrophes typographiques comprises : 35 % sur le même échantillon, 40 % sur
   les 1 983 titres.
4. Maquette : 6 cadres au plus, images de 1 600 pixels de large au plus.
5. Auteur absent de l'Annuaire : l'agent lui demande son rôle. Sans compte Notion : le ticket est
   créé sans auteur inscrit, et l'agent le dit.

## Sources lues

- `lib/notion.py` (R1) : client Notion existant ; `query_database` prend un filtre et un tri, sans limite,
  `markdown_to_blocks` ne fait pas de listes imbriquées, la création de page vise la base des
  rapports seulement. Aucune fonction ne rédige ni ne crée de ticket aujourd'hui.
- `lib/dashboard_api.py`, `lib/query.py`, `docs/interactive-dashboards.md` (R1) : `query_storage`
  écrit dans `dashboard_storage` ; la création de table par un script d'agent y est admise.
- `web/cron.py`, `web/cron_task.py`, `cron/sync-tags/` (R1) : format de `CRON.md`, lot `synchros`,
  aucune ligne à ajouter dans `cron.json`.
- `web/config.py`, `web/agents/cli.py` (R1) : l'e-mail de la personne connectée et l'identifiant de
  conversation sont transmis à l'agent.
- `skills/tally/scripts/query.py`, `tests/test_airtable.py` (R1) : forme des scripts de skill et de
  leurs tests.
- `docs/plans/2026-09-21-cron-lots-et-run-manuel.md` (R5) : décision sur les lots de crons.
- Chiffres (R2) : le seuil de la décision 3 est mesuré le 2026-10-30 sur 150 titres de l'export du
  Backlog unifié (2026-10-26) ; les bornes de la décision 4 viennent de la lecture de 7 maquettes
  réelles le 2026-10-30. L'âge d'un jour (décision 2) est un choix, pas une mesure.
- Vérifications d'API du 2026-10-30 : l'intégration Notion lit le backlog, l'Annuaire et les e-mails
  des comptes ; elle écrit l'emoji personnalisé dans un texte ; le jeton Figma lit un nœud de
  maquette avec l'en-tête `X-Figma-Token`.

## Questions ouvertes

Aucune. L'écriture de l'emoji a été essayée, et le seuil des doublons mesuré, avant validation.

## Validation

Validé par LJ le 2026-10-30.
