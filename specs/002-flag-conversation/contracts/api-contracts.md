# Phase 1 — Contrats d'interface

**Feature** : Bouton drapeau de signalement dans la barre de chat
**Date** : 2026-04-14

Cette feature expose deux interfaces publiques : les endpoints HTTP consommés par (a) la barre de chat (côté utilisateur), (b) le dashboard admin `data/interactive/conversations-echecs/`. Ce document fige leur forme pour servir de base aux tests.

---

## Endpoint 1 — `POST /api/conversations/{conv_id}/flag`

**Rôle** : toggle du signalement par l'utilisateur authentifié courant.

**Auth** : tout utilisateur authentifié pouvant accéder à la conversation (même règle que `GET /api/conversations/{conv_id}`).

**Requête**

```http
POST /api/conversations/abc-123/flag
Content-Type: application/json

{"reason": "La réponse est hors sujet"}
```

- `reason` : optionnel, chaîne, longueur ≤ 500 caractères. Absent = raison vide.

**Réponse — cas 1 : signalement créé ou mis à jour**

```http
200 OK
Content-Type: application/json

{
  "flagged": true,
  "flag_reason": "La réponse est hors sujet",
  "flag_user_id": "alice@example.com",
  "flagged_at": "2026-04-14T10:15:32+00:00"
}
```

**Réponse — cas 2 : signalement retiré (toggle OFF par le signalant lui-même)**

```http
200 OK
Content-Type: application/json

{
  "flagged": false,
  "flag_reason": null,
  "flag_user_id": null,
  "flagged_at": null
}
```

**Erreurs**

- `404 Not Found` — conversation inexistante.
- `403 Forbidden` — l'utilisateur ne peut pas accéder à la conversation.
- `422 Unprocessable Entity` — `reason` dépasse 500 caractères. Le corps contient un détail de la violation.

**Règles de transition** : voir `data-model.md > Transitions d'état`.

---

## Endpoint 2 — `DELETE /api/conversations/{conv_id}/flag`

**Rôle** : retrait inconditionnel d'un signalement, invoqué depuis le dashboard admin.

**Auth** : **admin-only** (`user_email in ADMIN_USERS`).

**Requête**

```http
DELETE /api/conversations/abc-123/flag
```

**Réponse**

```http
200 OK
Content-Type: application/json

{"flagged": false}
```

**Idempotence** : si la conversation n'est pas (ou plus) signalée, retour `200 OK` avec `{"flagged": false}` — pas d'erreur (EF-008).

**Erreurs**

- `404 Not Found` — conversation inexistante.
- `403 Forbidden` — utilisateur non admin.

---

## Endpoint 3 — `GET /api/conversations/flagged`

**Rôle** : lister toutes les conversations actuellement signalées. Consommé par `data/interactive/conversations-echecs/app.js`.

**Auth** : **admin-only** (`user_email in ADMIN_USERS`).

**Requête**

```http
GET /api/conversations/flagged
```

**Réponse**

```http
200 OK
Content-Type: application/json

{
  "conversations": [
    {
      "id": "abc-123",
      "title": "Conversation avec problème",
      "user_id": "alice@example.com",
      "flag_reason": "La réponse est hors sujet",
      "flagged_at": "2026-04-14T10:15:32+00:00"
    },
    ...
  ]
}
```

**Garanties**

- Les conversations sont triées par `flagged_at` décroissant (signalement le plus récent en tête). Cohérent avec l'UX d'un dashboard de triage.
- `user_id` est l'identifiant du **signalant** (`flag_user_id` en base), pas celui du propriétaire de la conversation. Choix produit explicite, documenté dans `data-model.md`.
- Liste vide → `{"conversations": []}`, pas de 404.

**Erreurs**

- `403 Forbidden` — utilisateur non admin.

---

## Interface UI — Bouton drapeau dans la barre de chat

**Rôle** : déclencheur côté utilisateur de `POST /flag`, ouvre un dialog de saisie de raison.

**Emplacement** : dans toutes les variantes de la barre de chat de `web/templates/explorations.html` — chat actif (`div.chat-bar`) et chat en lecture seule (`div.chat-bar-readonly`), hors mode « relaunch admin ».

**Structure HTML attendue** (simplifiée) :

```html
<button type="button"
        class="chat-flag-btn {% if current_conv.flagged_at %}flagged{% endif %}"
        id="chatFlagBtn"
        title="Signaler un problème"
        data-conv-id="{{ current_conv.id }}"
        data-current-reason="{{ current_conv.flag_reason or '' }}"
        data-current-flagger="{{ current_conv.flag_user_id or '' }}">
  <i class="ri-flag-line" aria-hidden="true"></i>
</button>

<dialog id="flagDialog">
  <form method="dialog">
    <label for="flagReason">Quel est le problème ?</label>
    <textarea id="flagReason" maxlength="500" placeholder="Décrivez brièvement (facultatif)…"></textarea>
    <p class="flag-counter"><span id="flagCounter">0</span>/500</p>
    <div class="flag-actions">
      <button type="button" id="flagCancel">Annuler</button>
      <button type="submit" id="flagSubmit">Signaler</button>
      <button type="button" id="flagRemove" hidden>Retirer le signalement</button>
    </div>
  </form>
</dialog>
```

**Garanties testables** :

1. Le bouton `#chatFlagBtn` est présent sur les pages conversation quelles que soient les conditions (chat interactif OU chat en lecture seule).
2. La classe `flagged` est présente sur le bouton si et seulement si la conversation a `flagged_at` non nul.
3. Le dialog `#flagDialog` contient un textarea avec `maxlength="500"` et un compteur visible.
4. Quand le dialog s'ouvre sur une conversation déjà signalée **par l'utilisateur courant**, le bouton « Retirer le signalement » est visible et la `<textarea>` est pré-remplie de la raison existante. Quand signalée par un autre utilisateur ou non signalée, le bouton « Retirer » reste masqué.
5. Au clic sur « Signaler » : `POST /api/conversations/{id}/flag` avec `{"reason": textarea.value}`. Au clic sur « Retirer » : `POST /api/conversations/{id}/flag` sans reason (comportement toggle OFF).

**Hors périmètre** : animation de confirmation, notification toast. La mise à jour visuelle du bouton après succès suffit pour la v1.
