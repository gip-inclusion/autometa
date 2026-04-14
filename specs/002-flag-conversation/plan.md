# Implementation Plan: Bouton drapeau de signalement dans la barre de chat

**Branch**: `002-flag-conversation` | **Date**: 2026-04-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-flag-conversation/spec.md`

## Summary

Ajouter un bouton drapeau dans la barre de chat (`web/templates/explorations.html`) permettant à un utilisateur authentifié de signaler une conversation, avec une raison facultative (≤ 500 caractères). Le signalement est persistédirectement sur la conversation via trois colonnes nullables (`flagged_at`, `flag_reason`, `flag_user_id`). Le dashboard `/interactive/conversations-echecs/` existe déjà et consomme deux endpoints à créer côté backend : `GET /api/conversations/flagged` (liste, admin-only) et `DELETE /api/conversations/:id/flag` (retrait, admin-only). Un endpoint supplémentaire `POST /api/conversations/:id/flag` est exposé pour le toggle utilisateur depuis la barre de chat.

## Technical Context

**Language/Version** : Python 3.11+ (FastAPI), Jinja2 côté templates, JavaScript vanilla côté front (htmx déjà présent mais non nécessaire ici).
**Primary Dependencies** : FastAPI, SQLAlchemy 2.0 (style `select()`), Alembic (migrations), `web.deps.get_current_user` (auth), `web.config.ADMIN_USERS`. Aucune nouvelle dépendance Python. Aucune nouvelle dépendance JS côté frontend.
**Storage** : PostgreSQL via SQLAlchemy ORM ; les colonnes de signalement sont ajoutées sur la table `conversations` existante. Migration Alembic autogénérée.
**Testing** : pytest + pytest-mock + TestClient FastAPI pour les endpoints (convention projet). Tests au niveau API (via `tests/conftest.py::client`) + tests de template pour le rendu du bouton.
**Target Platform** : Autometa sur Scalingo (prod), local via `make dev` et Docker compose (PostgreSQL + Redis déjà en place).
**Project Type** : Web application (FastAPI + Jinja templates + assets statiques vanilla JS).
**Performance Goals** : Pas de budget particulier. La liste admin des signalements est bornée en pratique (quelques centaines max) — pas de pagination nécessaire pour la v1.
**Constraints** : Longueur max de la raison = 500 caractères (spec EF-002). Endpoints de dashboard restreints à `ADMIN_USERS`. Modèle « un seul signalement actif par conversation, dernier gagne » (spec EF-006). Pas d'entrée orpheline au moment de la suppression d'une conversation (spec EF-009).
**Scale/Scope** : Ordre de grandeur — quelques dizaines à quelques centaines de conversations signalées simultanément, avec des traitements quotidiens par l'équipe qualité. Rien qui exige une optimisation particulière.

## Constitution Check

Vérification d'alignement avec `Constitution Autometa v1.1.0`.

| Principe | Statut | Justification |
|---|---|---|
| I. Lean & Simple First | ✅ | Trois colonnes sur `conversations`, zéro nouvelle table, zéro nouveau service. Réutilise `get_current_user`, `ADMIN_USERS`, le pattern des endpoints existants dans `web/routes/conversations.py`. Pas d'abstraction spéculative. |
| II. Sécurité par conception | ✅ | Entrée utilisateur (raison) validée côté backend (longueur ≤ 500). Échappement HTML déjà en place dans le dashboard. Endpoints admin-only vérifiés explicitement via `ADMIN_USERS`. Modèle de menaces dans la spec couvre XSS, spam, accès croisé. |
| III. Open Source & Transparence | ✅ | Code public ; décisions documentées dans cette spec et ce plan. Aucun secret. |
| IV. Impact mesurable | ✅ | Spec définit 5 critères de succès et 5 métriques de mesure d'impact (CS-001 à CS-005, tableau de métriques) avec cadence M+1 / M+3. |
| V. Lisibilité inter-équipes | ✅ | Spec en français, plan technique séparé. Termes métier simples (signalement, drapeau). |

**Zone critique touchée** : ⚠️ La PR modifie `web/models.py` et ajoute une migration dans `alembic/versions/` — les deux figurent dans `.claude/rules/zones-critiques.md`. **Ce changement touche une zone critique et nécessite une relecture humaine.** Le changement reste minimal (trois colonnes nullables + migration autogénérée revue), et le modèle « colonnes sur la conversation » est cohérent avec le pattern existant (`pinned_at`, `pinned_label`).

**Workflow** : une seule PR ; tests pytest pour chaque endpoint et pour le rendu du template ; lint + format ; revue humaine requise pour le modèle et la migration.

**Résultat de la porte (Phase 0)** : ✅ aucune violation. La zone critique est signalée et justifiée. Pas d'entrée dans Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/002-flag-conversation/
├── plan.md              # This file
├── spec.md              # Feature spec
├── research.md          # Phase 0 — décisions techniques
├── data-model.md        # Phase 1 — colonnes ajoutées, contraintes, transitions
├── quickstart.md        # Phase 1 — vérification locale
├── contracts/
│   └── api-contracts.md # Phase 1 — contrats des 3 endpoints + bouton
└── checklists/
    └── requirements.md  # Validation spec (déjà produite)
```

### Source Code (repository root)

Fichiers réellement touchés :

```text
web/
├── models.py                         # ⚠️ ZONE CRITIQUE : +3 colonnes sur Conversation (flagged_at, flag_reason, flag_user_id) + partial index
├── routes/conversations.py           # +3 endpoints : POST /flag (toggle), DELETE /flag (admin), GET /flagged (admin)
└── templates/explorations.html       # + bouton drapeau dans la barre de chat (interactive + readonly), + dialog de saisie raison, + JS toggle

alembic/versions/
└── <auto>_add_conversation_flag.py  # ⚠️ ZONE CRITIQUE : migration autogénérée puis revue

tests/
└── test_flag_conversation.py        # tests API (POST/DELETE/GET) + test rendu template

data/interactive/conversations-echecs/
└── (déjà existant)                  # aucun changement — déjà câblé sur les endpoints cibles
```

**Structure Decision** : Trois colonnes directement sur `conversations` plutôt qu'une table dédiée `conversation_flags`. Cohérent avec le pattern `pinned_at` / `pinned_label` déjà en place pour une autre propriété 1:1 optionnelle de la conversation. Évite une nouvelle table et une jointure pour le dashboard.

## Post-Design Constitution Re-check

Après rédaction de `research.md`, `data-model.md`, `contracts/api-contracts.md` et `quickstart.md` : aucune décision n'introduit de complexité supplémentaire qui changerait l'évaluation. La porte reste ✅. Relecture humaine requise (zone critique signalée).

## Complexity Tracking

> Aucune violation. Table volontairement vide.
