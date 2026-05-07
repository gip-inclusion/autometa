---
name: zendesk_query
description: Query Zendesk support tickets and comments for Emplois de l'Inclusion (read-only). (project)
---

# Zendesk Query Skill

Lecture seule des tickets et commentaires Zendesk du support Emplois.

## Configuration

Variables d'environnement (cf. `.env.example`) :

- `ZENDESK_SUBDOMAIN` — sous-domaine `<subdomain>.zendesk.com`
- `ZENDESK_EMAIL` — email du compte API
- `ZENDESK_API_TOKEN` — jeton API (Admin Center → Apps → API)

L'instance par défaut est `emplois`. Configurée dans `config/sources.yaml`.

## Usage

```python
from lib.sources import get_zendesk

zd = get_zendesk()

ticket = zd.get_ticket(12345)
# ZendeskTicket(id=12345, subject=..., status="solved", tags=[...], ...)

comments = zd.get_ticket_comments(12345)
# [ZendeskComment(public=True, author_role="end-user", body=..., ...), ...]

first_reply = zd.first_user_reply(12345)
# Premier commentaire end-user après la première réponse agent (la « clarification »).

for row in zd.iter_tickets([1, 2, 3], with_comments=True):
    # {"ticket_id": 1, "comments": [...]} — ou {"error": "..."} si le ticket est introuvable.
    ...
```

## Méthodes disponibles

| Méthode | Retour | Usage |
|---------|--------|-------|
| `get_ticket(ticket_id)` | `ZendeskTicket` | Métadonnées d'un ticket |
| `get_ticket_comments(ticket_id)` | `list[ZendeskComment]` | Tous les commentaires (oldest first) |
| `first_user_reply(ticket_id)` | `ZendeskComment \| None` | Première réponse end-user après le premier message agent |
| `iter_tickets(ids, with_comments=False)` | itérateur `dict` | Boucle batch avec gestion d'erreur par ticket et log de progression |
| `check_auth()` | `dict` | Vérifie les credentials (`users/me`) |

## Notes

- Le client gère un rate limit interne (~700 req/min) et fait du backoff sur HTTP 429 via `Retry-After`.
- Toutes les méthodes lèvent `ZendeskError(status_code, message)` sur erreur HTTP non-200 (sauf 429 retryé).
- Les commentaires utilisent le sideloading `users` pour exposer `author_role` (`end-user` / `agent` / `admin`).
- Pour des analyses cross-tickets, utiliser `iter_tickets` (logue tous les 500 et continue malgré les erreurs ponctuelles) plutôt que de boucler à la main.

## Quand l'utiliser

- Diagnostiquer une demande utilisateur précise (ticket #X)
- Extraire les premières clarifications sur un échantillon de tickets pour analyser les motifs de contact
- Recouper des tags / statuts avec des données Matomo ou Metabase
