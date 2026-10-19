# Suggérer de republier un tableau de bord modifié depuis sa publication

## Ce que je veux

Quand je modifie un tableau de bord que j'ai déjà publié, la version en ligne ne change pas
toute seule : elle reste figée sur ce qui était publié. Je veux être prévenu·e de ce décalage
et pouvoir republier d'un clic, pour que la version partagée reflète enfin mes changements.

## Ce qui devra marcher

DOD-1 — [du brief : « Si je change un tableau de bord qui est publié »] Quand j'ouvre la page d'un
tableau de bord dont au moins une version en ligne est en retard sur mes changements, une mention
visible m'avertit que la version en ligne ne reflète pas mes derniers changements — y compris
lorsqu'une autre version en ligne, elle, est déjà à jour.

DOD-2 — [du brief : « j'ai un bouton de suggestion : republier »] Cette mention comporte un unique
bouton « Republier » ; quand je clique dessus, toutes les versions en ligne en retard sont remises
en ligne avec mon contenu actuel, chacune sur son environnement.

DOD-3 — [décision : confirmation production] Si la version publique (« production ») fait partie
des versions à republier, une confirmation m'est demandée avant de remplacer la version vue par
tout le monde ; une version de test (« staging ») seule se republie sans confirmation.

DOD-4 — [du brief : « car sinon ce n'est pas publié »] Après la republication, les versions en
ligne reflètent mes changements et la suggestion disparaît ; si je recharge la page, l'état
affiché correspond toujours à la réalité du serveur.

DOD-5 — [tiré du brief : « un tableau de bord qui est publié »] Sur un tableau de bord qui n'a
aucune version en ligne, aucune mention ni bouton de republication n'apparaît : il n'y a rien à
republier.

DOD-6 — [tiré du brief : « Si je change »] Sur un tableau de bord dont toutes les versions en ligne
sont déjà à jour, aucune mention ni bouton de republication n'apparaît.

DOD-7 — [garde-fou : tableau non publiable] Sur un tableau de bord devenu non publiable (il utilise
l'API query) alors qu'il garde une version en ligne, aucun bouton de republication n'apparaît, et
un message m'explique que republier est indisponible.

DOD-8 — [garde-fou : échec de republication] Si la republication échoue, la ou les versions en
ligne restent inchangées, la suggestion demeure, et un message d'erreur lisible me signale
l'échec.

DOD-9 — [garde-fou : ne pas confondre avec « rafraîchir »] « Rafraîchir les données » d'une version
en ligne ne fait pas disparaître la suggestion de republier : rafraîchir ne remet pas mes
changements en ligne.

## Sources lues

- `web/templates/dashboard_detail.html` (R1) — l'écran de gestion d'un tableau de bord : bloc
  « Publier », mention passive « modifié depuis la dernière publication » (sans bouton), liste des
  versions en ligne avec leurs boutons (publier, dépublier, rafraîchir).
- `web/routes/dashboards.py` (R1) — route `dashboard_detail` et calcul `dashboard_drifted`
  (aujourd'hui global, fondé sur la publication la plus récente), route
  `POST /api/dashboards/{slug}/publish`.
- `web/publications.py` (R4 proche) — `publish` crée un snapshot figé et pousse le nouveau snapshot
  avant de retirer l'ancien ; `refresh` resynchronise le snapshot figé sans le recapturer ;
  `list_publications`.
- `web/models.py` (R1) — `Dashboard.updated_at`, `DashboardPublication.published_at`,
  `environment`, `unpublished_at`.
- `skills/publish_dashboard/` (R5) — opérations publish / unpublish / refresh / list.

## Questions ouvertes

Aucune. Deux décisions tranchées par la demandeuse : un unique bouton global qui republie toutes
les versions en retard d'un coup (DOD-2) ; confirmation requise avant de republier la version
publique (DOD-3).

## Validation

Validé par Annaelle Garcia le 2026-10-19.
