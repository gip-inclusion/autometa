# Phase 1 — Modèle de données

**Feature** : Bouton drapeau de signalement dans la barre de chat
**Date** : 2026-04-14

## Changements de schéma

Table affectée : `conversations` (table existante).

### Colonnes ajoutées

| Nom | Type SQLAlchemy | Nullable | Défaut | Description |
|---|---|---|---|---|
| `flagged_at` | `DateTime(timezone=True)` | Oui | `NULL` | Horodatage du signalement actif. `NULL` = conversation non signalée. C'est la colonne « maîtresse » de l'état de signalement. |
| `flag_reason` | `Text` | Oui | `NULL` | Raison libre saisie par l'utilisateur. Peut être `NULL` ou chaîne vide (non signalé / signalé sans raison). Longueur max : 500 caractères (validée côté application). |
| `flag_user_id` | `Text` | Oui | `NULL` | Identifiant de l'utilisateur signalant (même format que `Conversation.user_id` — e-mail ou identifiant passé par oauth-proxy). `NULL` si non signalé. |

### Index ajouté

| Nom | Type | Colonnes | Condition | Raison |
|---|---|---|---|---|
| `idx_conversations_flagged` | B-tree partiel | `flagged_at` | `WHERE flagged_at IS NOT NULL` | Accélère le listage admin `GET /api/conversations/flagged`. Pattern déjà utilisé sur `idx_conversations_needs_response`. |

### Invariants

- **Cohérence triplet** : `flagged_at`, `flag_reason`, `flag_user_id` sont toujours mis à jour ensemble. Un des trois est soit entièrement `NULL` (non signalé), soit `flagged_at` et `flag_user_id` non-nuls (et `flag_reason` peut être chaîne vide). Invariant géré au niveau application — pas de `CHECK` constraint PostgreSQL (voir Décision 3 de `research.md`).
- **Unicité** : par construction (colonnes sur la conversation), un seul signalement actif par conversation. Pas besoin de contrainte d'unicité explicite.
- **Suppression en cascade** : quand une conversation est supprimée (`DELETE FROM conversations WHERE id = ...`), les trois colonnes partent avec la ligne. EF-009 est satisfait gratuitement.

## Transitions d'état

Le « signalement » est un état porté par la conversation, pas une entité séparée. Trois états :

```text
(initial / unflagged)
       │
       │  POST /flag   (current user = U, reason = R)
       ▼
(flagged by U, reason R)
    │   │    │
    │   │    └─ POST /flag (current user = U) — toggle OFF
    │   │       ────────────────────────────── retour à (unflagged)
    │   │
    │   └─ POST /flag (current user = V ≠ U, reason R')
    │      ───────────────────────────────── (flagged by V, reason R') — « last wins »
    │
    └─ DELETE /flag (admin) — retour à (unflagged)
```

Équivalent SQL des transitions :

| Action | Effet |
|---|---|
| POST /flag, conv non signalée | `UPDATE conversations SET flagged_at = now(), flag_user_id = :current, flag_reason = :reason WHERE id = :id` |
| POST /flag, flaggée par `:current` | `UPDATE conversations SET flagged_at = NULL, flag_user_id = NULL, flag_reason = NULL WHERE id = :id` (toggle) |
| POST /flag, flaggée par un autre user | `UPDATE conversations SET flagged_at = now(), flag_user_id = :current, flag_reason = :reason WHERE id = :id` (overwrite) |
| DELETE /flag (admin) | `UPDATE conversations SET flagged_at = NULL, flag_user_id = NULL, flag_reason = NULL WHERE id = :id` (idempotent — pas d'erreur si déjà NULL) |

## Migration Alembic

- **Commande** : `alembic revision --autogenerate -m "add conversation flag columns"`
- **À vérifier après autogénération** :
  - Les trois colonnes sont bien ajoutées comme `nullable=True`.
  - Le partial index `idx_conversations_flagged` est présent avec la bonne clause `postgresql_where`.
  - `downgrade()` retire correctement l'index puis les colonnes (ordre inverse).
  - Pas de modification inattendue sur d'autres tables (Alembic peut détecter des drifts).
- **Idempotence** : `alembic upgrade head` est exécuté automatiquement au post-deploy Scalingo (`.claude/rules/sql.md`). La migration doit être appliquée une seule fois — les ajouts de colonnes nullables sont naturellement idempotents si on ne relance pas deux fois la même version.

## Mapping avec le contrat du dashboard existant

Le dashboard (`data/interactive/conversations-echecs/app.js`) attend la forme suivante pour chaque conversation dans `GET /api/conversations/flagged` :

| Clé JSON | Source |
|---|---|
| `id` | `conversations.id` |
| `title` | `conversations.title` |
| `user_id` | `conversations.flag_user_id` (l'utilisateur **signalant**, pas le propriétaire de la conversation) |
| `flag_reason` | `conversations.flag_reason` |
| `flagged_at` | `conversations.flagged_at` (sérialisé ISO 8601 — format déjà attendu par le dashboard via `new Date(isoDate)`) |

⚠️ Point d'attention : le champ `user_id` de la réponse JSON **n'est pas** `conversations.user_id` (propriétaire de la conversation). C'est `flag_user_id` (signalant). Le dashboard affiche « Utilisateur » en se référant au signalant, ce qui correspond bien à l'intention produit.
