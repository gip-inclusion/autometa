---
name: tally
description: Lire les formulaires et réponses Tally (tally.so) d'une instance — lister les formulaires, inspecter leur schéma, récupérer les réponses pour analyse. Lecture seule. À utiliser dès qu'une demande porte sur des données de formulaires/sondages Tally.
---

# Tally — lecteur de formulaires et réponses

Accès **lecture seule** à l'API Tally (`api.tally.so`) du compte de l'instance. Permet de lister les formulaires, d'inspecter leur schéma courant, et de récupérer les réponses comme source d'analyse.

Détails de conception et feuille de route (persistance, écriture, webhooks) : `docs/tally-integration.md`.

## Portée de la clé — à savoir

La clé API agit **au nom du compte utilisateur** qui l'a créée : elle voit **tous les workspaces dont ce compte est membre**, pas seulement un. `--workspaces` rend ce périmètre visible. Les réponses de formulaires sont souvent des **données personnelles** (emails, noms) — à manier avec prudence.

## Limites

- **Lecture seule, sans persistance.** Chaque commande appelle l'API en direct. Pas de cache (phase ultérieure).
- **Schéma courant uniquement.** `--schema` montre l'état actuel d'un formulaire ; pas d'historique de dérive (phase ultérieure).
- **Débit : 100 req/min.** La pagination des réponses est plafonnée (`--max-pages`, défaut 20 × 500) pour ne pas épuiser le budget.

## Commandes

```bash
# Workspaces visibles par la clé (périmètre)
.venv/bin/python skills/tally/scripts/query.py --workspaces

# Lister les formulaires (filtre workspace optionnel, appliqué côté client)
.venv/bin/python skills/tally/scripts/query.py --list [--workspace WS_ID]

# Schéma courant d'un formulaire (questions, types, uuid)
.venv/bin/python skills/tally/scripts/query.py --schema FORM_ID

# Réponses d'un formulaire
.venv/bin/python skills/tally/scripts/query.py --submissions FORM_ID \
    [--filter completed|partial|all] [--since 2026-01-01] [--until 2026-06-30] \
    [--limit 500] [--max-pages 20]
```

Sortie : JSON sur stdout. `--submissions` renvoie `{form_id, count, questions, submissions}` ; les réponses (`responses[]`) sont indexées par `questionId`, à corréler avec `questions`.
</content>
