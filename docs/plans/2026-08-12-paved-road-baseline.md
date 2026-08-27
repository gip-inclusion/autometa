<!-- Généré par `make paved-road-baseline` le 2026-08-12. Ne pas éditer les tableaux à la main :
     relancer la commande. -->

# Ligne de base du paved road — instrumentation, milestone 1

Produit par `make paved-road-baseline` (variante : `DAYS=30 make paved-road-baseline`). Toutes les
données proviennent de ce qui était déjà collecté : la base applicative (`conversations`,
`usage_events`, `cron_runs`), l'API GitHub Actions et l'historique git. Aucune collecte n'a été
ajoutée.

## Ce que cette exécution mesure — et ce qu'elle ne mesure pas

Les sections 1, 2 et 4 sortent de la base applicative. **Cette exécution a tourné sur une base locale
vide** : leurs zéros ne sont pas un résultat, ils disent seulement que la base de production n'est pas
accessible depuis un poste de développement. Relancer la commande avec le `DATABASE_URL` de
production pour obtenir la ligne de base réelle sur ces trois indicateurs.

Les sections 3 et 5 ne dépendent pas de la base : elles sont complètes et exploitables telles quelles.

## Lecture des sections 3 et 5

Le job `Security` de la CI échoue sur **21 %** des exécutions du workflow, à lui seul plus de quatre
fois le taux de `Tests` (5 %). Il concentre les trois quarts des échecs de job de la CI. **38 % des PR
finalement mergées** ont connu au moins un échec de workflow en chemin. C'est la donnée d'entrée du
ratchet : avant d'ajouter un gate, il y a un gate existant dont le bruit domine tous les autres.

Les deux planchers de couverture ont été posés le même jour (2026-07-17) et n'ont pas bougé depuis :
il n'y a pas encore de dérive à observer.

Fenêtre : depuis le 2026-05-14. Sources : base applicative, API GitHub, historique git. Aucune collecte nouvelle.

Proxy : une « fonctionnalité » est ici une conversation dont `pr_url` est non nul. `conv_type` ne connaît que `exploration`, `knowledge` et `report` : rien ne distingue aujourd'hui une conversation paved road d'une exploration ordinaire. Ce proxy ne retient que les parcours ayant abouti à une PR, donc il **surestime le succès** et sous-estime le coût moyen — les abandons sont invisibles.

## 1. Coût et durée par fonctionnalité

| indicateur | effectif | médiane | maximum |
|---|---|---|---|
| durée (minutes) | 0 | — | — |
| tokens (total) | 0 | — | — |
| tours | 0 | — | — |

| colonne de tokens | cumul sur la fenêtre |
|---|---|
| usage_input_tokens | 0 |
| usage_output_tokens | 0 |
| usage_cache_creation_tokens | 0 |
| usage_cache_read_tokens | 0 |

## 2. Fréquence des reprises humaines

| indicateur | valeur |
|---|---|
| conversations créées | 0 |
| dont avec PR | 0 |
| signalées (`flagged_at`) | 0 |
| en attente de réponse (`needs_response`) | 0 |

_Aucune donnée sur la fenêtre._

## 3. Bruit des gates

1498 exécutions de workflow, dont 94 en échec. 35 des 92 PR mergées ont connu au moins un échec (38 %).

| workflow | exécutions | échecs |
|---|---|---|
| dynamic/github-code-scanning/codeql | 977 | 4 |
| .github/workflows/ci.yml | 361 | 90 |
| .github/workflows/deploy-staging.yml | 84 | 0 |
| dynamic/dependabot/dependabot-updates | 44 | 0 |
| dynamic/dependabot/update-graph | 18 | 0 |
| .github/workflows/deploy-prod.yml | 14 | 0 |

| workflow | job | échecs | taux |
|---|---|---|---|
| .github/workflows/ci.yml | Security | 77 | 21 % |
| .github/workflows/ci.yml | Tests | 18 | 5 % |
| .github/workflows/ci.yml | Migrations | 4 | 1 % |
| dynamic/github-code-scanning/codeql | Analyze (javascript-typescript) | 4 | 0 % |
| dynamic/github-code-scanning/codeql | Analyze (python) | 3 | 0 % |
| dynamic/github-code-scanning/codeql | Analyze (actions) | 3 | 0 % |
| .github/workflows/ci.yml | Lint & format | 2 | 1 % |
| .github/workflows/ci.yml | Docker | 1 | 0 % |

## 4. Santé des tableaux de bord

_Aucune donnée sur la fenêtre._

## 5. Dérive du plancher de couverture

| date | commit | `coverage.report` | `diff_cover` |
|---|---|---|---|
| 2026-05-13 | 551949f1 | — | — |
| 2026-07-17 | f0e4a9ac | 74.9 | — |
| 2026-07-17 | c78ff516 | 74.9 | 90 |

