Zones critiques — toute modification de ces fichiers ou modules nécessite une relecture humaine.

Si tu touches à l'un de ces sujets, tu DOIS le signaler explicitement dans ta réponse avec la mention : « Ce changement touche une zone critique et nécessite une relecture humaine. »

Zones :

- `web/models.py` — Modèles SQLAlchemy (source de vérité du schéma). Toute modification génère une migration Alembic.
- `web/db.py` — Engine et session SQLAlchemy. Tout changement impacte chaque requête de l'application.
- `web/runner.py` — TaskRunner. Orchestre les agents, persiste les événements. Un bug ici casse toutes les conversations.
- `alembic/` — Migrations Alembic. Ne jamais modifier une migration existante, uniquement en ajouter.
- `web/agents/base.py` — Interface des backends agent et construction du system prompt.
- `docker-compose.yml`, `Dockerfile`, `entrypoint.sh` — Infrastructure de déploiement. Impact sur la production.
- `web/uploads.py` — Gestion des fichiers uploadés, scan antivirus. Surface de sécurité.
- `.claude/settings.json` — Permissions et skills de l'agent. Impact sur les capacités en production.
- `config/sources.yaml` — Credentials et URLs des sources de données.

## Zones de criticité secondaire — intégrations externes

Les clients d'API et modules qui interagissent avec des systèmes extérieurs sont des points de fragilité : un crash ou une régression peut mettre à plat l'ensemble du logiciel (conversations bloquées, données incorrectes, timeouts en cascade).

- `lib/matomo.py` — Client Matomo (HTTP, retry, parsing de réponses)
- `lib/metabase.py` — Client Metabase (HTTP, retry, parsing de résultats SQL)
- `lib/sources.py` — Résolution des credentials et URLs des sources
- `lib/api_signals.py` — Émission des signaux d'observabilité
- `web/s3.py` — Client S3 (stockage fichiers, sync)
- `web/notion.py` — Client Notion (publication rapports)
- `web/agents/cli.py` — Spawn et parsing du subprocess Claude CLI
- `web/agents/sdk.py` — Intégration claude-agent-sdk

Toute modification de ces modules doit :

- Être couverte par des tests avant et après le changement
- Ne pas introduire de régression sur le format des réponses ou des signaux
- Faire l'objet d'une validation manuelle si le comportement observable change (nouveau format de réponse, modification du retry, changement de timeout)
