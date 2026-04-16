# Phase 0 — Recherche technique

**Feature** : Bouton drapeau de signalement dans la barre de chat
**Date** : 2026-04-14

Aucun marqueur `NEEDS CLARIFICATION` ouvert. Les décisions ci-dessous fixent les choix techniques implicites avant la Phase 1.

## Décision 1 — Modèle de stockage : colonnes sur `conversations` vs table dédiée

- **Décision** : ajouter trois colonnes nullables à la table `conversations` existante : `flagged_at: DateTime(timezone=True)`, `flag_reason: Text`, `flag_user_id: Text`. Pas de nouvelle table.
- **Rationale** : la relation est strictement 1:1 (spec EF-006, un seul signalement actif par conversation) et le schéma existant utilise déjà ce pattern pour une autre propriété 1:1 optionnelle (`pinned_at`, `pinned_label` sur la même table). Respecter la cohérence du schéma (`.claude/rules/code.md` : « Respecter les patterns du fichier et du module »). Supprime une jointure au listage. La suppression automatique en cascade de la conversation (EF-009) est triviale : les colonnes disparaissent avec la ligne.
- **Alternatives écartées** :
  - *Table `conversation_flags`* : plus lourde (nouvelle table, FK avec ondelete CASCADE, jointure dans `GET /flagged`). N'apporte rien tant que la relation reste 1:1 et sans historique.
  - *Table générique `flags` avec `item_type`/`item_id`* (comme `pinned_items`) : nous n'avons qu'un seul type d'objet à signaler. L'abstraction est spéculative (YAGNI).

## Décision 2 — Index pour le listage admin

- **Décision** : ajouter un **partial index** `idx_conversations_flagged` sur `flagged_at` avec la condition `WHERE flagged_at IS NOT NULL`. Cela accélère `GET /api/conversations/flagged` et garde l'index minimal.
- **Rationale** : pattern déjà utilisé dans le projet (`idx_conversations_needs_response` avec `postgresql_where="needs_response = 1"`). Alembic gère correctement ce type d'index lors de l'autogénération — à vérifier en Phase 1.
- **Alternatives écartées** :
  - *Index non partiel* : occupe de l'espace pour les lignes non signalées (99 % des conversations).
  - *Pas d'index* : correct pour une table de quelques dizaines de milliers de lignes, mais le dashboard est admin et appelle souvent ; le coût de l'index est négligeable.

## Décision 3 — Limite de longueur côté backend

- **Décision** : la raison est stockée en `Text` (pas de limite au niveau colonne), mais validée côté application à 500 caractères (spec EF-002). Retour `422 Unprocessable Entity` si dépassement.
- **Rationale** : `Text` est simple et cohérent avec les autres colonnes textuelles de la table. La validation de longueur est métier, pas DB ; la mettre côté Pydantic/route la rend visible et testable. Éviter `CHECK` constraint PostgreSQL — plus difficile à modifier si la limite évolue et verbeux dans la migration.
- **Alternatives écartées** :
  - *`String(500)` + CHECK constraint* : plus strict mais moins flexible, et le pattern du projet privilégie `Text` pour les champs textuels.

## Décision 4 — Trois endpoints API distincts (sémantique claire)

- **Décision** : exposer trois endpoints :
  - `POST /api/conversations/{conv_id}/flag` — toggle pour l'utilisateur authentifié courant. Corps : `{"reason": "..."}` (optionnel, ≤ 500). Sémantique :
    - Conversation non signalée → crée le signalement avec `user_id = current_user`.
    - Conversation signalée par l'utilisateur courant → retire le signalement (comportement toggle, spec EF-005 scénario 4).
    - Conversation signalée par quelqu'un d'autre → remplace le signalement (last wins, spec EF-006).
  - `DELETE /api/conversations/{conv_id}/flag` — retrait inconditionnel. **Admin-only** (cf. clarification). Idempotent (EF-008).
  - `GET /api/conversations/flagged` — liste des conversations actuellement signalées. **Admin-only**. Format : `{"conversations": [{"id", "title", "user_id", "flag_reason", "flagged_at"}]}` (format imposé par le dashboard existant `data/interactive/conversations-echecs/app.js`).
- **Rationale** : la clarification Q1 de la spec restreint explicitement `GET /flagged` et `DELETE /flag` aux admins — c'est ce que le dashboard appelle. Le toggle utilisateur via `POST /flag` a une sémantique différente (toggle contextuel à l'utilisateur) ; lui donner son propre endpoint évite la surcharge d'un DELETE pour deux usages distincts. Pattern similaire au pin/unpin déjà présent dans `web/routes/conversations.py` (endpoints séparés + permissions différentes).
- **Alternatives écartées** :
  - *Un seul endpoint `PATCH /flag` avec payload `{"state": "on"|"off"}`* : plus verbeux côté client et mélange admin/non-admin. Évité.
  - *Toggle via `DELETE` également accessible aux non-admins* : contredit la clarification et donne à n'importe quel user le pouvoir d'effacer un signalement d'un autre user.

## Décision 5 — UX du bouton et de la saisie de raison

- **Décision** :
  - Bouton drapeau visible dans les trois variantes de barre de chat (`chat-bar`, `chat-bar-readonly`, `chat-bar-readonly` admin) de `explorations.html`. Icône Remixicon (`ri-flag-line` → `ri-flag-fill` quand actif), déjà dans le DS du projet (itou-theme).
  - Au clic : ouvre un petit dialog natif (ou `<dialog>` HTML) avec un `<textarea>` pré-rempli de la raison actuelle si existante, un compteur « x/500 », boutons « Signaler / Annuler ». Pas de modal Bootstrap (trop lourd pour ce besoin).
  - Si la conversation est déjà signalée par l'utilisateur courant, le dialog propose « Modifier » ou « Retirer le signalement ».
  - Au submit : appel à `POST /flag`. Au retour : mise à jour visuelle du bouton (classe `flagged`).
- **Rationale** : un simple `<dialog>` natif évite les dépendances JS supplémentaires, suit la contrainte UX de la spec (CS-001 : ≤ 15 s pour signaler), et se prête bien aux tests de rendu. Le bouton est placé dans la barre de chat (même conteneur que `chat-upload-btn` et `chat-send-btn`) pour rester visible sur toutes les conversations.
- **Alternatives écartées** :
  - *Inline input dans la barre de chat (pas de dialog)* : mélange la saisie du message agent avec la saisie de la raison, source de confusion.
  - *Popover / tooltip avec textarea* : plus fragile à positionner et moins accessible.
  - *Prompt JS natif (`prompt(...)`)* : limité (pas de saut de ligne, pas de compteur, style système), hors des patterns UI du projet.

## Décision 6 — Dépendance FastAPI pour l'accès admin

- **Décision** : introduire une dépendance `require_admin` (ou rule inline `user_email in ADMIN_USERS`) pour les deux endpoints admin. Le code existant de `web/routes/conversations.py` utilise déjà le pattern `if user_email not in ADMIN_USERS: raise HTTPException(403)` ; on le reprend sans créer de dépendance réutilisable tant qu'il n'y a que deux endpoints.
- **Rationale** : cohérence avec `web/routes/conversations.py` qui utilise ce pattern pour `POST /pin`, `DELETE /pin`, etc. Pas de généralisation prématurée (« Pas d'abstractions pour un seul usage », `.claude/rules/code.md`).
- **Alternatives écartées** :
  - *Dépendance FastAPI `Depends(require_admin)`* : propre mais inutile pour deux sites d'appel — sera faisable en refactor à 3+.

## Décision 7 — Stratégie de tests

- **Décision** : trois paliers :
  1. **Tests API** via `TestClient` existant (`tests/conftest.py::client`) : POST flag (nouveau + toggle + last-wins), DELETE flag (admin OK / non-admin refusé / idempotent), GET flagged (admin OK / non-admin refusé / format réponse).
  2. **Test migration Alembic** : exécuter la migration sur la base de test propre pour vérifier que `upgrade` et `downgrade` fonctionnent (partial index inclus).
  3. **Test rendu template** : rendre `explorations.html` avec une conversation flaggée et vérifier que le bouton drapeau porte la classe active, que la raison est pré-remplie dans le dialog, et symétriquement quand non flaggée.
- **Rationale** : couvre les trois surfaces (DB / API / UI). Conforme à `.claude/rules/tests.md` (pytest, parametrize pour les cas multiples, pas de mocks DB — on utilise la base `_test` existante via `conftest.py`).
- **Alternatives écartées** :
  - *Tests E2E Playwright/Selenium sur le dialog* : hors scope du projet (pas de framework E2E en place), ROI trop faible pour un bouton simple.
