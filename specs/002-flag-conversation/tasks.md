---
description: "Tasks: Bouton drapeau de signalement dans la barre de chat"
---

# Tasks: Bouton drapeau de signalement dans la barre de chat

**Input**: Design documents from `/specs/002-flag-conversation/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api-contracts.md`, `quickstart.md`

**Tests**: Inclus — convention projet `.claude/rules/tests.md` impose un test par modification de code.

**Organization**: Tâches groupées par user story après une phase Foundational (modèle + migration) bloquante pour US1 et US2.

## Format: `[ID] [P?] [Story] Description`

- **[P]** : parallélisable (fichiers différents, pas de dépendance bloquante).
- **[Story]** : US1 ou US2.
- Chemins absolus / repo-relatifs explicites.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Rien à initialiser — FastAPI, SQLAlchemy 2.0, Alembic, pytest, docker compose, chaîne `make dev / make test / make migrate` déjà en place.

*Aucune tâche.*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modèle et migration. US1 et US2 s'appuient sur les mêmes colonnes : à poser avant toute écriture de code métier.

**⚠️ ZONE CRITIQUE** : `web/models.py` et `alembic/versions/` sont listés dans `.claude/rules/zones-critiques.md`. Relecture humaine obligatoire sur la PR.

- [X] T001 Ajouter sur la classe `Conversation` de `web/models.py` les trois colonnes nullables `flagged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))`, `flag_reason: Mapped[str | None] = mapped_column(Text)`, `flag_user_id: Mapped[str | None] = mapped_column(Text)`. Ajouter dans `__table_args__` un partial index `Index("idx_conversations_flagged", "flagged_at", postgresql_where="flagged_at IS NOT NULL")`.
- [X] T002 Générer la migration Alembic : `alembic revision --autogenerate -m "add conversation flag columns"`. Vérifier dans `alembic/versions/<auto>_add_conversation_flag_columns.py` que : (a) les trois colonnes sont ajoutées comme nullable, (b) le partial index est créé avec la clause `postgresql_where`, (c) `downgrade()` retire l'index puis les colonnes dans l'ordre inverse, (d) aucune modification inattendue sur d'autres tables. Corriger manuellement si besoin.
- [X] T003 Appliquer la migration sur la base locale et la base de test : `make migrate` puis vérifier via `psql` que la table `conversations` contient les trois colonnes et l'index (`\d+ conversations`).

**Checkpoint** : base prête. Les endpoints et templates peuvent maintenant être implémentés.

---

## Phase 3: User Story 1 — Signaler un problème sur une conversation en cours (Priority: P1) 🎯 MVP

**Goal**: Un utilisateur authentifié peut cliquer sur le bouton drapeau dans la barre de chat, saisir une raison facultative (≤ 500 caractères), et voir la conversation marquée comme signalée. Toggle OFF si clic sur son propre signalement.

**Independent Test**: Ouvrir une conversation (`/explorations/<id>`) en tant qu'utilisateur non admin, cliquer sur le bouton drapeau, saisir « hors sujet », valider. Rafraîchir la page : le bouton reste en état « signalé ». Cliquer à nouveau → dialog avec bouton « Retirer » → cliquer → le drapeau redevient vide.

### Tests for User Story 1

> **NOTE** : écrire ces tests AVANT l'implémentation ; ils doivent échouer sur la base actuelle.

- [X] T004 [P] [US1] Créer `tests/test_flag_conversation.py` et y ajouter une classe/groupe `TestPostFlag` paramétré couvrant : (a) conversation non signalée → `POST /flag {"reason":"..."}` par `user_alice` renvoie 200 avec `flagged=true`, raison, user_id, flagged_at ISO ; (b) même utilisateur repost sur conversation déjà flaggée par lui → toggle OFF (réponse avec `flagged=false`, colonnes à NULL en base) ; (c) deuxième utilisateur `user_bob` post sur conversation flaggée par `user_alice` → overwrite (`flag_user_id = user_bob`) ; (d) POST avec raison de 501 caractères → 422 ; (e) POST sur conversation inexistante → 404 ; (f) POST sans champ `reason` → 200 avec raison vide.
- [X] T005 [P] [US1] Dans `tests/test_flag_conversation.py`, ajouter un test `TestRenderFlagButton` qui rend `web/templates/explorations.html` via `web.deps.templates.get_template(...).render(current_conv=<factory>, is_shared=False, can_upload=True, current_user=...)` pour deux cas : (a) conversation non flaggée → le HTML contient `id="chatFlagBtn"` sans la classe `flagged` ; (b) conversation flaggée par l'utilisateur courant → la classe `flagged` est présente et `data-current-reason` est renseigné. Inclut aussi un assert sur `maxlength="500"` du `<textarea id="flagReason">`.

### Implementation for User Story 1

- [X] T006 [US1] Dans `web/routes/conversations.py`, ajouter la route `@router.post("/{conv_id}/flag")` avec une dépendance `user_email: str = Depends(get_current_user)`. Corps : un modèle Pydantic `FlagBody(BaseModel)` avec `reason: str = Field(default="", max_length=500)`. Logique : récupérer la conversation via SQLAlchemy 2.0 `session.scalars(select(Conversation).where(...))`, 404 si absente ; appliquer la table de transition du `data-model.md` (create / toggle off / overwrite) en fonction de `conv.flag_user_id` ; committer ; retourner `{"flagged": bool, "flag_reason": ..., "flag_user_id": ..., "flagged_at": ...}` avec l'horodatage ISO 8601.
- [X] T007 [US1] Dans `web/routes/conversations.py`, faire en sorte que la route `GET /api/conversations/{conv_id}` (déjà existante, ligne ~219) inclue dans sa réponse les champs `flagged_at`, `flag_reason`, `flag_user_id`, afin que le template puisse refléter l'état au rechargement. Si la route existante ne passe pas `current_conv` au template mais uniquement du JSON : s'assurer que la route Jinja (probablement `GET /explorations/{id}`) transmet bien l'objet `Conversation` complet (ou les trois champs) dans le contexte du template.
- [X] T008 [US1] Dans `web/templates/explorations.html`, ajouter le bouton drapeau `#chatFlagBtn` et le `<dialog id="flagDialog">` selon la structure HTML figée dans `contracts/api-contracts.md > Interface UI`. Placer le bouton dans les trois variantes de `chat-bar-container` (chat actif `div.chat-bar`, `chat-bar-readonly` utilisateur, et admin-relaunch), à côté du `chat-send-btn`. Utiliser l'icône `ri-flag-line` / `ri-flag-fill`. Renseigner les `data-conv-id`, `data-current-reason`, `data-current-flagger` depuis `current_conv`.
- [X] T009 [US1] Ajouter dans `web/templates/explorations.html` (bloc `{% block scripts %}`) le JS qui gère : ouverture/fermeture du dialog, compteur de caractères temps réel, pré-remplissage de la textarea avec `data-current-reason`, affichage conditionnel du bouton `#flagRemove` (visible si et seulement si `data-current-flagger === currentUserEmail`), submit → `fetch('/api/conversations/{id}/flag', {method:'POST', body: JSON.stringify({reason})})`, mise à jour de la classe `flagged` sur `#chatFlagBtn` selon la réponse. Utiliser un identifiant d'utilisateur courant déjà exposé côté template (injecter un `data-current-user` sur `body` ou équivalent si nécessaire).
- [X] T010 [P] [US1] Dans `web/static/css/style.css` (ou le fichier de style de `explorations.html` s'il est séparé), ajouter les règles pour `.chat-flag-btn` (neutre, contour), `.chat-flag-btn.flagged` (remplissage d'accent) et `#flagDialog` (mise en forme minimale du dialog natif, compteur, boutons d'action). Se caler sur les variables CSS du thème Itou déjà en place.
- [X] T011 [US1] Faire passer T004 et T005 : `make test tests/test_flag_conversation.py`. Les deux groupes doivent être verts. Itérer si besoin sur T006-T009.

**Checkpoint** : US1 fonctionnelle. Un utilisateur peut signaler / retirer son signalement depuis la barre de chat, et l'état persiste correctement en base et dans le template.

---

## Phase 4: User Story 2 — Traiter les signalements depuis le dashboard (Priority: P2)

**Goal**: Un administrateur peut ouvrir `/interactive/conversations-echecs/` et voir la liste des signalements actifs, cliquer sur « Retirer » pour en supprimer un.

**Independent Test**: Avec au moins un signalement en base (posé via US1 ou directement via SQL dans le test), se connecter avec un user admin, ouvrir le dashboard → la conversation apparaît. Cliquer sur « Retirer » → la ligne disparaît sans rechargement. Rafraîchir → elle ne revient pas.

### Tests for User Story 2

> **NOTE** : écrire avant l'implémentation.

- [ ] T012 [P] [US2] Dans `tests/test_flag_conversation.py`, ajouter un groupe `TestGetFlagged` couvrant : (a) admin + 2 conversations flaggées → 200 OK, clé `conversations` contient les deux entrées avec `{id, title, user_id, flag_reason, flagged_at}`, triées `flagged_at` décroissant (récent en tête) ; (b) admin + aucune conversation flaggée → `{"conversations": []}` ; (c) non-admin → 403 ; (d) vérifier que le champ `user_id` de la réponse correspond bien à `conversations.flag_user_id` (signalant), pas à `conversations.user_id` (propriétaire).
- [ ] T013 [P] [US2] Dans `tests/test_flag_conversation.py`, ajouter un groupe `TestDeleteFlag` couvrant : (a) admin + conversation flaggée → 200 OK `{"flagged": false}`, colonnes à NULL en base ; (b) admin + conversation déjà non-flaggée → 200 OK `{"flagged": false}` (idempotent, pas d'erreur) ; (c) non-admin → 403 ; (d) conversation inexistante → 404.
- [ ] T014 [P] [US2] Dans `tests/test_flag_conversation.py`, ajouter un test `TestCascadeOnConversationDelete` : créer une conversation flaggée puis appeler `DELETE /api/conversations/{id}` (route existante) et vérifier qu'aucune entrée orpheline ne reste en base (EF-009). La cascade est naturelle puisque les colonnes partent avec la ligne — ce test documente l'invariant.

### Implementation for User Story 2

- [ ] T015 [US2] Dans `web/routes/conversations.py`, ajouter la route `@router.get("/flagged")` avec `user_email: str = Depends(get_current_user)`. Si `user_email not in ADMIN_USERS` → `raise HTTPException(403)`. Sinon : `session.scalars(select(Conversation).where(Conversation.flagged_at.is_not(None)).order_by(Conversation.flagged_at.desc()))`, sérialiser en `{"conversations": [{"id", "title", "user_id": c.flag_user_id, "flag_reason", "flagged_at": c.flagged_at.isoformat()}]}`. ⚠️ Attention à l'ordre de déclaration : la route `/flagged` **doit** être déclarée avant la route paramétrée `/{conv_id}` pour éviter que FastAPI la confonde avec un `conv_id="flagged"`.
- [ ] T016 [US2] Dans `web/routes/conversations.py`, ajouter `@router.delete("/{conv_id}/flag")` avec `user_email: str = Depends(get_current_user)`. Si `user_email not in ADMIN_USERS` → 403. Sinon : récupérer la conversation, 404 si absente ; mettre les trois colonnes à NULL ; commit ; retourner `{"flagged": false}`. Idempotent par construction (UPDATE sans filtre sur `flagged_at`).
- [X] T017 [US2] Faire passer T012, T013, T014 : `make test tests/test_flag_conversation.py -k "Flagged or Delete or Cascade"`. Itérer sur T015-T016 si nécessaire.

**Checkpoint** : US2 livrée. Le dashboard `/interactive/conversations-echecs/` est câblé de bout en bout ; US1 et US2 fonctionnent indépendamment mais se complètent.

---

## Phase N: Polish & Cross-Cutting Concerns

- [X] T018 [P] Exécuter `make lint` et corriger toute violation sur `web/models.py`, `web/routes/conversations.py`, `web/templates/explorations.html`, `tests/test_flag_conversation.py`, `alembic/versions/<auto>_*.py`.
- [X] T019 [P] Exécuter `make test` (suite complète) pour s'assurer qu'aucun autre test n'est cassé par l'ajout des colonnes ou la modification du template (notamment les tests existants sur `explorations.html` et `web/routes/conversations.py`).
- [ ] T020 Exécuter manuellement le quickstart sections 2, 3 et 4 (flux utilisateur, flux admin, cas d'erreur) — cf. `specs/002-flag-conversation/quickstart.md`.
- [ ] T021 Sur le déploiement prod : la migration Alembic sera appliquée automatiquement au post-deploy Scalingo (cf. `.claude/rules/sql.md`). Vérifier au premier déploiement via `scalingo -a autometa-prod logs --filter alembic` que `upgrade head` s'est bien exécuté. Pas d'action manuelle si tout se passe bien.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** : vide.
- **Foundational (Phase 2)** : T001 → T002 → T003 (strictement séquentiel : le modèle avant la migration, la migration avant l'exécution). **Bloque US1 et US2**.
- **US1 (Phase 3)** : peut démarrer après T003.
- **US2 (Phase 4)** : peut démarrer après T003 (indépendant de US1 au niveau test — on peut insérer des flags directement en SQL dans les fixtures de test sans passer par `POST /flag`).
- **Polish (Phase N)** : après US1 et US2 complets pour T018-T020 ; T021 au moment du déploiement.

### Contraintes intra-story

- **US1** : T004, T005, T010 (fichiers distincts) parallélisables entre eux. T006 avant T007 avant T008/T009 (route → contexte template → template HTML → JS). T011 en fin de phase.
- **US2** : T012, T013, T014 (même fichier de test mais groupes distincts — par prudence, non marqués `[P]` entre eux) ; T015 avant T016 (ordre de déclaration FastAPI) ; T017 en fin.

### Inter-stories

- US1 et US2 touchent **tous les deux** `web/routes/conversations.py` — les tâches T006/T007 (US1) et T015/T016 (US2) ne doivent PAS être faites simultanément par deux développeurs sans coordination (conflits de merge garantis).
- US1 et US2 peuvent néanmoins être livrées dans deux PRs séparées : si c'est le cas, US2 dépend de US1 uniquement pour le modèle (déjà dans Phase 2), pas pour le code de route.

### Parallel Opportunities

- Phase 3 : T004 ‖ T005 ‖ T010 (tests API, tests template, CSS — trois fichiers différents).
- Phase 4 : T012, T013, T014 sont techniquement dans le même fichier de test mais dans des groupes distincts ; on peut les rédiger en parallèle si on fait attention aux conflits de merge.
- Phase N : T018 ‖ T019.

---

## Parallel Example: User Story 1

```bash
# Phase 3 — étape d'écriture parallèle
Task: "Créer tests/test_flag_conversation.py avec TestPostFlag (T004)"
Task: "Ajouter TestRenderFlagButton dans tests/test_flag_conversation.py (T005)"
Task: "Ajouter les styles .chat-flag-btn dans web/static/css/style.css (T010)"

# Puis séquentiellement :
Task: "Implémenter POST /api/conversations/{conv_id}/flag (T006)"
Task: "Injecter flag_* dans le contexte du template (T007)"
Task: "Ajouter bouton + dialog dans explorations.html (T008)"
Task: "Ajouter le JS du dialog et du toggle (T009)"
Task: "Lancer make test pour valider (T011)"
```

---

## Implementation Strategy

### MVP First (US1 seule)

1. Phase 2 complète (T001 → T003). ⚠️ Zone critique — relire la migration avec attention.
2. Phase 3 complète (T004 → T011).
3. **STOP & VALIDATE** : flux user complet en local. `make test` vert.
4. Déployer. À cette étape, le dashboard admin ne fonctionne pas encore (404 ou tableau vide sur l'endpoint), mais l'équipe peut commencer à poser des signalements.
5. Phase N (T018-T020) sur le MVP.

### Incremental Delivery

1. MVP (Phase 2 + Phase 3) → première PR, mergée et déployée. Les utilisateurs peuvent signaler.
2. Phase 4 (US2) → seconde PR, débloque le dashboard admin.
3. Phase N au fil des PR.

### Parallel Team Strategy

Avec deux développeurs :

1. Dev A et Dev B font Phase 2 ensemble (T001 → T003), zone critique.
2. Ensuite :
   - Dev A : Phase 3 (US1).
   - Dev B : Phase 4 (US2). Ils coordonnent leurs modifs sur `web/routes/conversations.py` (rebase fréquent) et sur `tests/test_flag_conversation.py`.
3. Merge séquentiel ou PR combinée selon préférence équipe.

---

## Notes

- `[P]` = fichiers différents, aucune dépendance incomplète.
- `[Story]` rattache la tâche à US1 ou US2.
- Convention projet : test avant code (`.claude/rules/tests.md`).
- ⚠️ `web/models.py` et `alembic/versions/` sont des zones critiques (cf. `.claude/rules/zones-critiques.md`) — relecture humaine requise sur la PR contenant T001-T003.
- Migration appliquée automatiquement au post-deploy Scalingo (T021) — vérifier les logs au premier déploiement.
