# Implementation Plan: Intégration Matomo Tag Manager sur Autometa

**Branch**: `001-matomo-tag-manager` | **Date**: 2026-04-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-matomo-tag-manager/spec.md`

## Summary

Poser sur Autometa un point d'injection unique pour le snippet de chargement d'un conteneur Matomo Tag Manager, piloté par une variable d'environnement portant l'ID du conteneur. Quand l'ID est défini, le snippet officiel Matomo (chargement asynchrone, non bloquant) est rendu une seule fois dans `web/templates/base.html` ; quand l'ID est vide, rien n'est rendu. Toute instrumentation analytique ultérieure (tags, déclencheurs, variables) est gérée depuis l'interface MTM, sans nouveau changement de code.

## Technical Context

**Language/Version** : Python 3.11+ (FastAPI), Jinja2 templates côté rendu HTML.
**Primary Dependencies** : FastAPI + `fastapi.templating.Jinja2Templates` (déjà câblé via `web/deps.py`), `python-dotenv` (déjà utilisé par `web/config.py`). Aucune nouvelle dépendance.
**Storage** : N/A — feature purement frontend/template. Aucun modèle SQLAlchemy à modifier.
**Testing** : pytest + pytest-mock (convention projet — cf. `.claude/rules/tests.md`). Tests de rendu de template via `Jinja2Templates`.
**Target Platform** : Application web Autometa déployée sur Scalingo (prod) ; exécution locale en dev (`make dev`).
**Project Type** : Web application (FastAPI server + templates Jinja). Pas de séparation backend/frontend distincte.
**Performance Goals** : Aucun budget perf supplémentaire ; le snippet MTM est le snippet officiel asynchrone (non bloquant). Cible : pas de régression > 5 % sur le First Contentful Paint des pages principales (CS-003).
**Constraints** : Snippet rendu **une seule fois** dans le code (un seul fichier de template touché). Si la variable d'env est vide → zéro injection (pas même une balise vide). Pas de code applicatif Python qui pousse des événements à MTM (cf. intention utilisateur « le reste géré par l'interface »).
**Scale/Scope** : Toutes les pages d'Autometa qui héritent de `web/templates/base.html` (≈ une dizaine de templates aujourd'hui : `accueil`, `connaissances`, `cron`, `explorations`, `rapports`, `rechercher`, plus partials de `routes/conversations.py`). Hors périmètre : apps interactives sous `/interactive/`.

## Constitution Check

Vérification d'alignement avec `Constitution Autometa v1.1.0`.

| Principe | Statut | Justification |
|---|---|---|
| I. Lean & Simple First | ✅ | Une variable d'env + un bloc Jinja conditionnel dans un template existant. Aucune abstraction, aucun helper dédié, aucune nouvelle dépendance. Réutilisation directe de `web/config.py` et `web/deps.py`. |
| II. Sécurité par conception | ✅ | L'ID de conteneur est lu via `web/config.py` (pas de hardcode). Le snippet officiel Matomo est rendu tel quel ; l'ID est interpolé via Jinja qui échappe par défaut. URL Matomo (HTTPS) déjà utilisée par le projet. Modèle de menaces de la spec couvre les vecteurs (gouvernance MTM, indispo serveur Matomo). |
| III. Open Source & Transparence | ✅ | Code public, ID de conteneur côté client de toute façon visible dans la page. Décision documentée ici et dans la spec. |
| IV. Impact mesurable | ✅ | CS-001 à CS-005 et tableau « Mesure d'impact » de la spec définissent les métriques avant lancement. La mesure « délai entre demande de tag et mise en prod » sera observable dès qu'un premier tag sera publié depuis MTM. |
| V. Lisibilité inter-équipes | ✅ | Spec en français, plan technique séparé. Aucun jargon métier nouveau introduit. |

**Sections obligatoires des specs** : modèle de menaces et mesure d'impact présents dans `spec.md`.

**Workflow** : changement minimal, une seule PR ; tests pytest accompagneront la modification ; aucun fichier listé dans `.claude/rules/zones-critiques.md` n'est touché (`base.html` n'y figure pas).

**Résultat de la porte (Phase 0)** : ✅ aucune violation. Pas de table de complexité à remplir.

## Project Structure

### Documentation (this feature)

```text
specs/001-matomo-tag-manager/
├── plan.md              # This file
├── spec.md              # Feature spec (déjà produite)
├── research.md          # Phase 0 — décisions techniques résolues
├── quickstart.md        # Phase 1 — comment vérifier en local
├── contracts/
│   └── template-contract.md  # Phase 1 — contrat du snippet rendu
└── checklists/
    └── requirements.md  # Validation spec (déjà produite)
```

Pas de `data-model.md` : la fonctionnalité n'introduit aucune entité persistée (rien dans `web/models.py`, aucune migration Alembic).

### Source Code (repository root)

Les fichiers réellement touchés par cette feature :

```text
web/
├── config.py            # + lecture de MATOMO_TAG_MANAGER_CONTAINER_ID et de l'URL Matomo (MATOMO_URL ou réutilisation d'une valeur déjà disponible)
├── deps.py              # + exposition des deux valeurs comme globals Jinja (templates.env.globals)
└── templates/
    └── base.html        # + bloc conditionnel rendant le snippet MTM officiel dans <head> (point d'injection unique)

tests/
└── test_matomo_tag_manager.py   # tests de rendu : snippet présent quand ID set, absent sinon
```

**Structure Decision** : Pas de nouvelle arborescence. Trois fichiers existants modifiés, un fichier de test ajouté. Cohérent avec le pattern actuel du projet (config → globals Jinja → template).

## Post-Design Constitution Re-check

Après la rédaction de `research.md`, `contracts/template-contract.md` et `quickstart.md` (Phase 1) : aucun nouvel élément n'introduit de complexité ou de risque qui changerait l'évaluation ci-dessus. La porte reste ✅.

## Complexity Tracking

> Aucune violation de la constitution à justifier — table volontairement vide.
