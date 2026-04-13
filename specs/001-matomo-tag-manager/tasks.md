---
description: "Tasks: Intégration Matomo Tag Manager sur Autometa"
---

# Tasks: Intégration Matomo Tag Manager sur Autometa

**Input**: Design documents from `/specs/001-matomo-tag-manager/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `contracts/template-contract.md`, `quickstart.md`

**Tests**: Inclus — la convention projet (`.claude/rules/tests.md`, CLAUDE.md) impose un test pour chaque modification de code.

**Organization**: Tasks are grouped by user story. La feature étant volontairement minimale, US1 concentre l'ensemble du code à écrire ; US2 est entièrement résolue par configuration côté Matomo (aucune tâche de code).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story tag (US1, US2)
- File paths are absolute or repo-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Aucune initialisation projet nécessaire — le serveur FastAPI, les templates Jinja, `pytest`, et la chaîne `make dev / make test` sont déjà en place.

*Aucune tâche.*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Aucun pré-requis bloquant. Le pattern config → globals Jinja → template existe déjà dans `web/deps.py` (`static_url`, `format_relative_date`).

*Aucune tâche.*

---

## Phase 3: User Story 1 — Instrumenter le site sans redéploiement (Priority: P1) 🎯 MVP

**Goal**: Charger le conteneur Matomo Tag Manager sur toutes les pages héritant de `web/templates/base.html`, à un seul endroit dans le code, piloté par variable d'environnement, no-op si l'ID est absent.

**Independent Test**: Lancer `make dev` avec `MATOMO_TAG_MANAGER_CONTAINER_ID` défini → inspecter une page (ex. `/`) et vérifier la présence du snippet officiel MTM dans `<head>`. Recommencer sans la variable → vérifier l'absence totale du snippet. Conforme au contrat dans `contracts/template-contract.md`.

### Tests for User Story 1

> **NOTE**: Écrire ces tests AVANT l'implémentation et vérifier qu'ils échouent sur la base actuelle.

- [X] T001 [P] [US1] Créer `tests/test_matomo_tag_manager.py` avec deux tests paramétrés via `@pytest.mark.parametrize` couvrant : (a) `matomo_tag_manager_container_id` non vide → le HTML rendu de `web/templates/base.html` contient exactement une balise `<script>` avec `g.async = true` et une `g.src` de la forme `{matomo_url}/js/container_{id}.js`, dans `<head>` avant `{% block head %}` ; (b) ID vide → aucun marqueur `Matomo Tag Manager`, aucun `_mtm`, aucune balise `<script>` MTM. Utiliser le fixture `mocker` de pytest-mock pour patcher `web.deps.templates.env.globals` ; rendre le template via `templates.get_template("base.html").render(...)`.

### Implementation for User Story 1

- [X] T002 [P] [US1] Ajouter dans `web/config.py` deux variables : `MATOMO_TAG_MANAGER_CONTAINER_ID = os.getenv("MATOMO_TAG_MANAGER_CONTAINER_ID", "")` et `MATOMO_URL = os.getenv("MATOMO_URL", "https://matomo.inclusion.beta.gouv.fr")`. Placer les déclarations près des autres lectures de config Matomo si elles existent, sinon en fin de fichier dans une section cohérente.
- [X] T003 [US1] Dans `web/deps.py`, exposer les deux valeurs comme globals Jinja, à la suite de `templates.env.globals["format_relative_date"] = format_relative_date` :
      `templates.env.globals["matomo_tag_manager_container_id"] = config.MATOMO_TAG_MANAGER_CONTAINER_ID` et `templates.env.globals["matomo_url"] = config.MATOMO_URL`. Dépend de T002.
- [X] T004 [US1] Dans `web/templates/base.html`, juste avant `{% block head %}{% endblock %}` à l'intérieur de `<head>`, ajouter un bloc `{% if matomo_tag_manager_container_id %} ... {% endif %}` contenant le snippet officiel Matomo Tag Manager (cf. `contracts/template-contract.md` pour la forme exacte). L'URL du `g.src` doit utiliser les variables Jinja `{{ matomo_url }}` et `{{ matomo_tag_manager_container_id }}`. Dépend de T003.
- [X] T005 [US1] Faire passer T001 : exécuter `make test` ; les deux cas paramétrés doivent maintenant être verts.

**Checkpoint** : User Story 1 fully functional. Le snippet se charge sur toutes les pages héritant de `base.html` quand l'ID est défini, et reste totalement absent sinon.

---

## Phase 4: User Story 2 — Respect du consentement et de la vie privée (Priority: P2)

**Goal**: La collecte respecte la politique de consentement retenue pour Autometa.

**Independent Test**: Avec un conteneur publié dont les tags sont configurés selon la politique de consentement choisie (exemption CNIL ou bandeau), vérifier en navigateur que le déclenchement des tags suit cette politique.

**Aucune tâche de code** : par décision produit (cf. `Clarifications` de la spec), la politique de consentement est entièrement gérée dans la configuration des tags et déclencheurs côté interface Matomo Tag Manager. Une fois US1 livrée, US2 est traitée par une action côté Matomo, pas par une modification du code Autometa.

- [ ] T006 [US2] **(côté Matomo, pas côté code)** Configurer dans l'interface Matomo Tag Manager la politique de consentement retenue pour Autometa (exemption CNIL pour l'analytique auto-hébergée, ou intégration d'un bandeau de consentement) puis publier une nouvelle version du conteneur. Étape effectuée par une personne habilitée Matomo, hors PR de code.

**Checkpoint** : US1 + US2 livrées ; toute évolution analytique ultérieure passe désormais par MTM.

---

## Phase N: Polish & Cross-Cutting Concerns

- [X] T007 [P] Documenter la nouvelle variable d'environnement `MATOMO_TAG_MANAGER_CONTAINER_ID` dans `.env.example` (la laisser vide par défaut). Ajouter aussi `MATOMO_URL=https://matomo.inclusion.beta.gouv.fr` en commentaire si la variable n'y figure pas déjà.
- [ ] T008 Définir `MATOMO_TAG_MANAGER_CONTAINER_ID` (et au besoin `MATOMO_URL`) sur l'environnement Scalingo de production : `scalingo -a autometa-prod env-set MATOMO_TAG_MANAGER_CONTAINER_ID=<ID>`. À effectuer une fois le conteneur MTM publié au moins une fois (sinon `/js/container_<ID>.js` renvoie 404).
- [X] T009 Exécuter `make lint` et corriger toute violation introduite dans `web/config.py`, `web/deps.py`, `tests/test_matomo_tag_manager.py`.
- [ ] T010 Exécuter manuellement `quickstart.md` étapes 1 à 4 (vérification présence/absence du snippet, requête réseau OK, arrivée des hits dans Matomo en temps réel).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** : vide.
- **Foundational (Phase 2)** : vide.
- **User Story 1 (Phase 3)** : peut commencer immédiatement.
- **User Story 2 (Phase 4)** : nécessite que US1 soit en production (sinon le conteneur n'est chargé nulle part).
- **Polish (Phase N)** : T007 et T009 dès que le code US1 est écrit ; T008 au moment du déploiement ; T010 une fois T008 effectuée.

### Within User Story 1

- T001 (test) **avant** T004 (implémentation template) — vérifier que T001 échoue d'abord.
- T002 (config) **avant** T003 (deps.py l'importe).
- T003 **avant** T004 (le template lit les globals exposés par deps.py).
- T005 (`make test`) **après** T002, T003, T004.

### Parallel Opportunities

- T001 (création du fichier de test) et T002 (ajout dans `web/config.py`) touchent des fichiers différents → marqués `[P]`, peuvent être faits en parallèle.
- T007 (`.env.example`) est indépendant des fichiers de code → marqué `[P]`.

---

## Parallel Example: User Story 1

```bash
# Lancer en parallèle :
Task: "Créer tests/test_matomo_tag_manager.py avec les deux cas paramétrés"
Task: "Ajouter MATOMO_TAG_MANAGER_CONTAINER_ID et MATOMO_URL dans web/config.py"
```

Ensuite, séquentiellement : T003 → T004 → T005.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 / Phase 2 : rien à faire.
2. Phase 3 : T001 → (T002 ‖ T001 déjà en parallèle) → T003 → T004 → T005.
3. **STOP & VALIDATE** : `make test` vert ; vérification visuelle locale via le quickstart (étapes 1 et 2) avec un ID de test.
4. Polish : T007 et T009.
5. Déploiement : T008.
6. Validation prod : T010.

### Incremental Delivery

US1 livrée seule = MVP fonctionnel : le snippet est en place, prêt à recevoir n'importe quel tag publié depuis MTM. US2 est ensuite résolue par une action côté Matomo (T006), sans nouvelle PR de code.

---

## Notes

- `[P]` = fichiers différents, aucune dépendance.
- `[Story]` rattache la tâche à US1 ou US2 pour la traçabilité.
- Convention projet : un test précède toute modification de code (`.claude/rules/tests.md`).
- Penser à pousser les variables d'env sur Scalingo en plus de `.env` local (rappel mémoire utilisateur).
- Aucun fichier listé dans `.claude/rules/zones-critiques.md` n'est touché ; relecture humaine standard suffit.
