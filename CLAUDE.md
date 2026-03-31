# Matometa

Assistant analytics pour l'Inclusion (Matomo + Metabase → analyses en français).

```bash
make dev       # Serveur local (lance autometa)
make test      # Tests (hors intégration)
make lint      # ruff check + format check
make format    # Auto-format
make migrate   # Migrations Alembic
make ci        # lint + security + test
```

Architecture et flux de données : `.claude/ARCHITECTURE.md`.

Conventions de code : `.claude/rules/code.md`. Tests (pytest, pytest-mock, parametrize, factories) : `.claude/rules/tests.md`.

## Contexte métier

IAE (insertion par l'activité économique) — programme français d'emploi avec trois types d'acteurs :

- **Candidats** (demandeurs d'emploi) — Ont besoin d'un diagnostic pour obtenir un « pass IAE » valable deux ans. Candidatent via des prescripteurs ou en autonomie.
- **Prescripteurs** — Accompagnent les candidats. Les « prescripteurs habilités » peuvent réaliser des diagnostics et délivrer des pass.
- **Employeurs** (SIAE) — Structures employant les titulaires de pass. Nécessitent un conventionnement annuel.

Sources de données :

- **Matomo** → Comportement utilisateur sur les sites web (visites, événements, parcours)
- **Metabase** → Données statistiques (candidatures, démographie, stats SIAE)

## Sites web

| Site | URL | ID Matomo | Fiche knowledge |
|---|---|---|---|
| Emplois | emplois.inclusion.beta.gouv.fr | 117 | emplois.md |
| Marché | lemarche.inclusion.gouv.fr | 136 | marche.md |
| Pilotage | pilotage.inclusion.gouv.fr | 146 | pilotage.md |
| Communauté | communaute.inclusion.gouv.fr | 206 | communaute.md |
| Dora | dora.inclusion.beta.gouv.fr | 211 | dora.md |
| Plateforme | inclusion.gouv.fr | 212 | plateforme.md |
| RDV-Insertion | www.rdv-insertion.fr | 214 | rdv-insertion.md |
| Mon Récap | mon-recap.inclusion.beta.gouv.fr | 217 | mon-recap.md |

## Chemins clés

| Chemin | Rôle |
|---|---|
| `config/sources.yaml` | Configuration des sources de données |
| `knowledge/sites/` | Contexte par site — lire avant de requêter |
| `knowledge/matomo/README.md` | Référence API Matomo |
| `data/cache/matomo/` | Baselines Matomo par site (synchro quotidienne depuis PostgreSQL) |
| `data/cache/metabase/` | Inventaire cartes et dashboards Metabase (synchro quotidienne) |
| `DATABASE_URL` (PostgreSQL) | Conversations, rapports, files d'attente agent, etc. |
| `data/interactive/` | Fichiers téléchargeables (servis à `/interactive/`) |

## Dépôts GitHub

| Site | Dépôt | Branche |
|---|---|---|
| Emplois | `gip-inclusion/les-emplois` | master |
| Marché | `gip-inclusion/le-marche` | master |
| Communauté | `gip-inclusion/la-communaute` | master |
| Pilotage | `gip-inclusion/pilotage` | master |
| Dora | `gip-inclusion/dora` | master |
| RDV-Insertion | `gip-inclusion/rdv-insertion` | master |

Utiliser `raw.githubusercontent.com` ou l'API GitHub contents pour explorer le code.
