# Tasks: Dashboard d'audit Tag Manager

**Branch**: `003-tm-audit-dashboard`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Tests**: explicitly requested in spec (FR-005, CS-003) — included.

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Vérifier que la branche `003-tm-audit-dashboard` est checked out et propre (`git status`).
- [X] T002 Vérifier que la base Postgres locale tourne pour les tests (`docker compose ps db`).

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T003 Étendre `config/sources.yaml` avec la section `tag_manager.sites` (10 sites copiés depuis la branche `louije/tm-explorer`).
- [X] T004 Ajouter `get_tag_manager_sites()` dans `lib/sources.py` (lecture de `config["tag_manager"]["sites"]`).
- [X] T005 Exposer un block `body_class` dans `web/templates/base.html` (pour permettre `no-sidebar` sur la page Tag Manager).

**Checkpoint** : configuration et base de templates prêtes — User Story 1 peut commencer.

## Phase 3: User Story 1 - Audit en lecture seule des tags déployés (Priority: P1) 🎯 MVP

**Goal** : à partir de `/tag-manager`, un utilisateur sélectionne un site, voit ses triggers, sélectionne un trigger, voit les tags qu'il déclenche.

**Independent Test** : `make dev`, ouvrir `/tag-manager`, cliquer sur Emplois → voir les triggers ; cliquer sur un trigger → voir les tags filtrés.

### Tests (TDD — écrits avant l'implémentation)

- [X] T006 [P] [US1] Créer `tests/test_tag_manager_dashboard.py` avec fixtures `SITES`, `CONTAINER`, `EXPORT` et fixture `mock_matomo` qui patche `web.routes.tag_manager.get_tag_manager_sites` + `web.routes.tag_manager.execute_matomo_query` (jamais d'instanciation `MatomoAPI`).
- [X] T007 [US1] Test `test_tag_manager_page_lists_configured_sites` (GET `/tag-manager` renvoie 200 et contient les noms de sites).
- [X] T008 [US1] Test `test_triggers_fragment_lists_triggers` (GET `/tag-manager/sites/117/triggers` renvoie 200 + noms des triggers).
- [X] T009 [US1] Test `test_tags_fragment_filtered_by_trigger` paramétré par `(trigger_id, expected_tag, not_expected_tag)`, vérifie le filtrage par `fireTriggerIds`.
- [X] T010 [US1] Test `test_triggers_fragment_unknown_site_returns_404`.
- [X] T011 [US1] Test `test_triggers_fragment_handles_no_live_release` (container sans environnement `live`).
- [X] T012 [US1] Test `test_matomo_error_returns_generic_message_no_secret_leak` (erreur Matomo ne fait pas fuiter le détail dans la réponse).
- [X] T013 [US1] Test `test_route_does_not_instantiate_matomo_api` (assertion sur `lib.matomo.MatomoAPI.__init__`).

### Implémentation

- [X] T014 [US1] Créer `web/routes/tag_manager.py` avec un `APIRouter` et la fonction interne `_find_site(matomo_id)` qui retourne le site ou raise `HTTPException(404)`.
- [X] T015 [US1] Implémenter `_matomo_call(method, params)` dans `web/routes/tag_manager.py` qui wrappe `execute_matomo_query` (instance="inclusion", caller=`CallerType.APP`, timeout=30).
- [X] T016 [US1] Implémenter `_live_export(site)` dans `web/routes/tag_manager.py` : appelle `TagManager.getContainer`, trouve la release `environment="live"`, appelle `TagManager.exportContainerVersion`. Retourne `(container, export, error)`. Logue toute erreur en `logger.warning("...%s", site_id)`.
- [X] T017 [US1] Endpoint `GET /tag-manager` : rend `tag_manager.html` avec sidebar + `sites=get_tag_manager_sites()`.
- [X] T018 [US1] Endpoint `GET /tag-manager/sites/{matomo_id}/triggers` : `_find_site` + `_live_export`, rend `_tag_manager_triggers.html`. Sur erreur Matomo → `HTTPException(502, "Erreur lors de la récupération du conteneur")`.
- [X] T019 [US1] Endpoint `GET /tag-manager/sites/{matomo_id}/triggers/{trigger_id}/tags` : idem + filtre `tags` où `trigger_id in tag.fireTriggerIds`. Rend `_tag_manager_tags.html`.
- [X] T020 [P] [US1] Créer `web/templates/tag_manager.html` (3 panneaux, htmx sur chaque site row, `body_class=no-sidebar`).
- [X] T021 [P] [US1] Créer `web/templates/_tag_manager_triggers.html` (boutons trigger avec `hx-get` vers l'endpoint tags, états vides : pas de version live / pas de triggers).
- [X] T022 [P] [US1] Créer `web/templates/_tag_manager_tags.html` (carte trigger + liste de cartes tags, état vide : aucun tag).
- [X] T023 [P] [US1] Ajouter le bloc CSS `.tm-*` dans `web/static/css/style.css` (depuis `louije/tm-explorer` : layout 3 panneaux, badges types, cartes).
- [X] T024 [US1] Enregistrer `tag_manager.router` dans `web/app.py` (avant `html.router` qui a des catch-all).
- [X] T025 [US1] Ajouter un lien `/tag-manager` dans `web/templates/accueil.html` (bouton dans la grille de navigation, icône `ri-price-tag-3-line`).

**Checkpoint US1** : `make lint && make test` passent ; visite manuelle `/tag-manager` valide le parcours du § Quickstart du plan.

## Phase 4: Polish & Cross-Cutting Concerns

- [X] T026 [P] Vérifier qu'aucun fichier `web/static/js/tag_manager*.js` n'a été créé (`ls web/static/js/`).
- [X] T027 [P] Vérifier qu'aucun fichier `lib/_*.py` n'a été créé hors `__init__.py` (`find lib/ -name '_*.py' -not -name '__init__.py'`).
- [ ] T028 Renommer la branche `003-tm-audit-dashboard` en `louije/feat/tag-manager-dashboard` (convention PR template du dépôt) avant push.
- [ ] T029 Smoke test manuel : ouvrir `/tag-manager`, cliquer 3 sites différents, cliquer 3 triggers différents par site, vérifier qu'aucune erreur n'apparaît dans la console serveur ni le réseau navigateur.

## Dependencies

- Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4.
- Au sein de US1 : T006 bloque T007-T013. T014-T016 bloquent T017-T019. T020-T023 sont parallélisables. T024-T025 viennent après T017. Le smoke test T029 vient après tout le reste.

## Parallel Execution Examples

- Tests : T007-T013 peuvent être écrits en lot après T006 (même fichier, mais sections distinctes — pas de [P] entre eux car même fichier).
- Templates : T020 / T021 / T022 / T023 sont 4 fichiers distincts → exécution parallèle possible.
- Polish : T026 et T027 sont des `ls`/`find` indépendants → parallèles.

## Implementation Strategy

- **MVP** = Phase 1 + 2 + 3. La Phase 4 est de la vérification, pas du périmètre fonctionnel.
- Pas de découpage en sous-PRs : la PR couvre l'ensemble US1 (les 3 endpoints sont indissociables sur le plan UX).
- Approche TDD : tests T006-T013 avant implémentation T014-T019. Templates et CSS peuvent venir avant ou après les tests (ils ne sont pas couverts par les tests unitaires de route).
