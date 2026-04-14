# Phase 1 — Quickstart : vérifier le bouton drapeau et le dashboard

**Feature** : Bouton drapeau de signalement dans la barre de chat
**Date** : 2026-04-14

## Pré-requis

- Docker compose up (`docker compose up -d` — PostgreSQL + Redis + MinIO).
- `.env` configuré (au minimum `DATABASE_URL`, `DEFAULT_USER`, `ADMIN_USERS`).
- Migrations Alembic appliquées : `make migrate`.

## 1. Vérifier les tests automatisés

```bash
make test
```

`tests/test_flag_conversation.py` couvre :

- `POST /flag` — création, toggle OFF (même user), overwrite (autre user), validation longueur 500.
- `DELETE /flag` — admin OK, non-admin 403, idempotent sur conversation non signalée.
- `GET /flagged` — admin OK (format + tri décroissant), non-admin 403, liste vide.
- Rendu de `explorations.html` — bouton présent, classe `flagged` conditionnelle, dialog contenant `maxlength=500`.

## 2. Vérifier manuellement le flux utilisateur

1. `make dev` → ouvrir <http://localhost:5000>.
2. Se connecter comme utilisateur **non-admin** (ex. `DEFAULT_USER` différent de `ADMIN_USERS`).
3. Ouvrir une conversation existante (`/explorations/<id>`).
4. Cliquer sur le bouton drapeau dans la barre de chat. Le dialog s'ouvre.
5. Saisir « la réponse est hors sujet » (compteur affiche « 32/500 »).
6. Valider. Le bouton devient visuellement « rempli » (classe `flagged`).
7. Rafraîchir la page. Le bouton reste rempli (état persisté).
8. Cliquer à nouveau sur le bouton. Le dialog s'ouvre ; le bouton « Retirer le signalement » est visible. Cliquer dessus.
9. Le bouton redevient vide. Rafraîchir → confirmé.

## 3. Vérifier le dashboard admin

1. Se reconnecter comme utilisateur **admin** (présent dans `ADMIN_USERS`).
2. Avant de tester le dashboard, créer au moins un signalement (étapes 4-6 ci-dessus, ou via API directe : `curl -X POST http://localhost:5000/api/conversations/<id>/flag -d '{"reason":"..."}'`).
3. Ouvrir <http://localhost:5000/interactive/conversations-echecs/>.
4. Vérifier que la liste affiche la conversation signalée avec : titre (lien), identifiant du signalant, raison, horodatage.
5. Cliquer sur « Retirer ». La ligne disparaît sans rechargement.
6. Revenir à la conversation (via le lien puis manuellement dans `/explorations/<id>`). Le bouton drapeau est redevenu vide.

## 4. Vérifier les cas d'erreur

- Saisir une raison de 501 caractères dans le dialog → le `maxlength=500` côté HTML empêche la saisie. Forcer l'envoi via l'API avec une raison trop longue : `curl -X POST .../flag -d '{"reason":"a…"*501}'` → 422.
- Appel `GET /api/conversations/flagged` avec un user non admin (header `X-Forwarded-Email:non-admin@example.com`) → 403.
- Supprimer une conversation signalée via `DELETE /api/conversations/<id>` → le signalement doit disparaître du dashboard au rafraîchissement.

## 5. Lint et format

```bash
make lint
```

Aucune violation attendue sur `web/models.py`, `web/routes/conversations.py`, `web/templates/explorations.html`, `tests/test_flag_conversation.py`.

## Critères de succès vérifiables ici

- **CS-001** : mesurer le temps entre clic sur drapeau et confirmation visible → attendu ≤ 15 s sur le flux manuel.
- **CS-002** : après signalement, ouvrir le dashboard dans la minute → l'entrée apparaît au plus tard au prochain refresh.
- **EF-008** (idempotence) : appeler `DELETE /flag` deux fois de suite → les deux retournent 200 OK.
- **EF-009** (suppression en cascade) : supprimer la conversation → le dashboard ne contient plus d'entrée orpheline pour elle.
