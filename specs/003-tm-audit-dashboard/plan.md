# Implementation Plan: Dashboard d'audit Tag Manager

**Branch**: `003-tm-audit-dashboard` | **Date**: 2026-05-02 | **Spec**: [spec.md](./spec.md)

## Summary

Page web read-only `/tag-manager` listant pour chaque site Matomo configuré les conteneurs Tag Manager, leurs triggers et tags publiés en production. Layout 3 panneaux. Aucune écriture exposée. Reprend la base graphique de `louije/tm-explorer` ; réécriture du code Python et suppression du JS custom au profit d'htmx.

## Technical Context

**Language/Version**: Python 3.14 (existant)
**Primary Dependencies**: FastAPI (existant), Jinja2 (existant), htmx 2.x (déjà chargé dans `base.html`), `lib.query.execute_matomo_query`
**Storage**: N/A (pas de persistance, lecture API Matomo uniquement)
**Testing**: pytest + pytest-mock + Starlette `TestClient` (existants)
**Target Platform**: Linux server (Scalingo), browsers desktop modernes
**Project Type**: web-service (FastAPI monolithe — `web/` + `lib/`)
**Performance Goals**: < 3s de latence perçue par requête utilisateur (1 conteneur ≈ 2 appels Matomo TagManager.getContainer + TagManager.exportContainerVersion)
**Constraints**: Pas d'instanciation directe de `MatomoAPI` ; pas de fichier `_*.py` ; pas de JS custom ; logging paramétré ; erreurs génériques côté client
**Scale/Scope**: ~10 utilisateurs internes, ~10 sites configurés, audit ad-hoc

## Constitution Check

| Principe | Statut | Notes |
|---|---|---|
| I. Lean & Simple First | ✅ | Réutilise `lib.query.execute_matomo_query`, `lib.sources.load_config`, `lib.matomo.MatomoAPI.request`/`post`. Aucune nouvelle abstraction. |
| II. Sécurité par conception | ✅ | Modèle de menaces dans la spec. Pas de secret en clair, auth déléguée au proxy, formatage paramétré du logging, erreurs génériques côté client (cf. alertes CodeQL #136-138 de la PR #34). |
| III. Open Source & Transparence | ✅ | Aucun code obfusqué, aucun secret en dur. |
| IV. Impact mesurable | ⚠️ | Pas de métrique de référence quantitative formelle (l'outil n'existe pas avant). Valeur cible qualitative : audit possible sans accès à l'UI Matomo. Acceptable car outil interne ad-hoc. |
| V. Lisibilité inter-équipes | ✅ | Spec en français, vocabulaire métier (trigger / tag / conteneur) repris de l'UI Matomo. |

Aucune violation justifiable nécessitant la table de complexité.

## Project Structure

```text
specs/003-tm-audit-dashboard/
├── spec.md
├── plan.md
├── checklists/requirements.md
└── tasks.md             ← généré par /speckit.tasks

config/sources.yaml                       ← +section tag_manager.sites
lib/sources.py                            ← +get_tag_manager_sites()
web/app.py                                ← +include_router(tag_manager.router)
web/routes/tag_manager.py                 ← nouveau, 3 endpoints
web/templates/base.html                   ← block body_class
web/templates/accueil.html                ← lien vers /tag-manager
web/templates/tag_manager.html            ← page principale (3 panneaux)
web/templates/_tag_manager_triggers.html  ← partial htmx
web/templates/_tag_manager_tags.html      ← partial htmx
web/static/css/style.css                  ← +CSS .tm-*
tests/test_tag_manager_dashboard.py       ← pytest (parametrize, mocker)
```

**Structure Decision** : monolithe FastAPI existant. Nouveau router dans `web/routes/`, nouveaux templates dans `web/templates/`, tests dans `tests/`. Aucun nouveau package.

## Phase 0: Research

Aucune NEEDS CLARIFICATION dans la spec. Trois choix techniques à documenter (consigné dans `research.md`).

## Phase 1: Design & Contracts

### Data model

Aucune table SQL, aucun stockage. Trois entités proviennent de l'API Matomo et sont rendues telles quelles :

- **Site Tag Manager** : config locale (`name`, `matomo_id`, `container_id`, `staging?`).
- **Container** : `TagManager.getContainer` → `{draft, releases[]}`.
- **Export** : `TagManager.exportContainerVersion` → `{triggers[], tags[], variables[]}`.

### Contrats d'interface (HTTP)

| Méthode | Path | Réponse | Statuts d'erreur |
|---|---|---|---|
| GET | `/tag-manager` | HTML page complète (panneau sites rempli, autres vides) | — |
| GET | `/tag-manager/sites/{matomo_id}/triggers` | Fragment HTML : liste de boutons trigger | 404 site inconnu, 502 erreur Matomo |
| GET | `/tag-manager/sites/{matomo_id}/triggers/{trigger_id}/tags` | Fragment HTML : carte trigger + cartes tags filtrés par `fireTriggerIds` | 404 site/trigger inconnu, 502 erreur Matomo |

Le corps des erreurs 502 est un message générique en français. Le détail est loggé en `logger.warning("TagManager.X failed for site %s", site_id)`.

### Quickstart (manuel)

1. `make dev`
2. Visiter `http://localhost:8001/tag-manager`
3. Cliquer sur un site (ex. Emplois) → le panneau central liste les triggers
4. Cliquer sur un trigger → le panneau de droite liste les tags qui le déclenchent

## Complexity Tracking

Aucune violation. Section vide.
