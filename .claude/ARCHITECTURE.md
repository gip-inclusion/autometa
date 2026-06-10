# Architecture

## Vue d'ensemble

FastAPI multi-workers avec exécution d'agents distribuée via Redis. Chaque worker uvicorn consomme une file de tâches partagée (liste Redis) ; les notifications SSE passent par Redis pub/sub, donc n'importe quel worker peut servir n'importe quel flux. La concurrence est bornée par `MAX_CONCURRENT_AGENTS` par worker.

## Couches

**`web/`** — Application FastAPI, routes, templates Jinja2, SSE, TaskRunner (`web/runner.py`), backends agent (`web/agents/`). Dépend de `lib/`.

**`lib/`** — Clients API Matomo et Metabase, interface de requête unifiée, observabilité. Ne connaît pas FastAPI.

**`skills/`** — Capacités agent. Chaque skill a un `SKILL.md` et un `scripts/`.

**`knowledge/`** — Base de connaissances markdown, structurée par domaine.

**`config/`** — Configuration des sources de données (`sources.yaml`, substitution `${env.VAR}`).

## Flux principaux

**Conversation** : POST message → persistance DB → `runner.submit()` pousse la tâche dans la liste Redis → boucle consumer d'un worker → spawn agent CLI (stream-json) → parse events → persist en DB → publication pub/sub → SSE → navigateur. L'annulation et le marqueur de fin de run passent aussi par Redis (pub/sub + clé `done`).

**Requête API** : Agent exécute Python → `lib.query.execute_*_query()` → client API avec retry → signal d'observabilité sur stdout → TaskRunner parse → DB.

## Déploiement

| Environnement | DB | File/SSE | Stockage |
|---|---|---|---|
| Local (docker-compose) | PostgreSQL | Redis | S3 (MinIO) |
| Scalingo | PostgreSQL addon | Redis addon | S3 (Scaleway) |

PostgreSQL et Redis sont requis dans tous les environnements (`DATABASE_URL`, `REDIS_URL`).
