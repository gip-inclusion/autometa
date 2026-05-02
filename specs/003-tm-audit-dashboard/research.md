# Research — Dashboard d'audit Tag Manager

## Décision 1 — Endpoints htmx vs API JSON

- **Choix** : 3 endpoints renvoyant des fragments HTML.
- **Raison** : élimine le JS custom (retour @vperron sur PR #34), aligne sur le reste du projet (`accueil.html`, `rechercher.html` utilisent htmx + partials).
- **Alternatives rejetées** : API JSON + JS de rendu côté client — c'est ce que faisait `louije/tm-explorer` (452 lignes de JS), jugé trop verbeux et fragile.

## Décision 2 — Cache de l'export Matomo

- **Choix** : aucun cache. Appel Matomo direct par requête.
- **Raison** : volume faible (~10 utilisateurs), `httpx.Client` réutilise les connexions, latence 2 GET par sélection acceptable.
- **Alternatives rejetées** : cache Redis 60s — YAGNI tant qu'on n'a pas mesuré la lenteur.

## Décision 3 — Source de la liste des sites

- **Choix** : section `tag_manager.sites` dans `config/sources.yaml`, lue par `lib.sources.get_tag_manager_sites()`.
- **Raison** : cohérent avec `metabase.dashboards`, `data_inclusion.datawarehouse` ; le skill `tag_manager` peut consommer la même source.
- **Alternatives rejetées** : variables d'environnement (10 sites = 30 vars, illisible) ; appel `Matomo.getSitesWithAtLeastViewAccess` (ne fournit pas le `container_id`).
