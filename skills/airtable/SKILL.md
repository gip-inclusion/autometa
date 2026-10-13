---
name: airtable
description: Lire les tables et enregistrements Airtable (suivi des commandes et devis Mon Récap) — lister les tables d'une base, lire une table ou une vue. Lecture seule. À utiliser dès qu'une demande porte sur des données Airtable ou sur les commandes et devis Mon Récap.
---

# Airtable — lecteur de tables

Accès **lecture seule** à l'API Airtable (`api.airtable.com`). Permet d'inspecter le schéma d'une base (tables, champs, vues) et de lire les enregistrements d'une table ou d'une vue, comme source d'analyse.

## Bases connues

| Base | Identifiant | Contenu |
|---|---|---|
| Mon Récap | `apppGMTgMw5lav2d1` | Commandes et devis (ex. table `tblMe0DsXWKTAZN1d`, vue des devis non validés `viwizmpNR5XNOT59s`) |

## Portée du jeton — à savoir

Le jeton (`AIRTABLE_TOKEN`) agit **au nom du compte Airtable** qui l'a créé : il lit **toutes les bases auxquelles ce compte a accès**, pas seulement celles listées ci-dessus. Ne lire que ce que la demande exige.

Les enregistrements contiennent des **données personnelles** (noms, emails, téléphones) : ne pas les recopier dans une réponse, un rapport ou un `data.json` public au-delà du strict nécessaire.

## Limites

- **Lecture seule.** Aucune création, modification ni suppression d'enregistrement.
- **Débit : 5 requêtes par seconde et par base.** La pagination est automatique (100 enregistrements par page) et plafonnée (`--max-pages`) ; un avertissement signale un résultat tronqué.
- **Schéma** : `tables` exige que le jeton ait le droit de lire le schéma des bases ; sans lui, l'erreur le dit, et `records` reste utilisable avec les identifiants connus.

## Commandes

```bash
# Tables d'une base, avec leurs champs et leurs vues
.venv/bin/python skills/airtable/scripts/query.py tables BASE_ID

# Enregistrements d'une table, ou d'une vue (ordre et filtres de la vue appliqués)
.venv/bin/python skills/airtable/scripts/query.py records BASE_ID TABLE \
    [--view VIEW] [--field "Nom" --field "Statut"] [--formula "{Statut} = 'À valider'"] [--max-pages 100]
```

Sortie : JSON sur stdout. `records` renvoie `{count, records}`, chaque enregistrement portant `id`, `createdTime` et `fields` (les champs vides sont absents). Tables et vues s'adressent par identifiant (`tbl…`, `viw…`) ou par nom.

## Tableaux de bord

Un `cron.py` lit Airtable via `query_airtable` de la façade `lib.dashboard_api` (cf. `docs/interactive-dashboards.md`).
