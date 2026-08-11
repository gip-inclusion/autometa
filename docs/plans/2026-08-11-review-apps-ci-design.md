# Review apps pilotées par la CI — design

Date : 2026-08-11
Statut : validé, prêt pour le plan d'implémentation

## Problème

Les review apps Scalingo existent (`scalingo.json` seed `AUTOMETA_ENV=review` et
`OAUTH2_PROXY_REDIRECT_URL` sur le domaine de la PR) mais se déclenchent à la main depuis le
dashboard Scalingo. Rien ne les crée, ne les met à jour ni ne les supprime automatiquement, et leur
existence n'est corrélée à aucun état de la pull request.

On veut un cycle de vie lié à la PR : création à l'ouverture, mise à jour quand le code change,
destruction à la fermeture — le tout décidé par la CI, sur un dépôt public, sans exposer les
identifiants de production.

## État constaté

Relevé sur l'infrastructure au 2026-08-11 :

| Élément | Valeur |
|---|---|
| Dépôt | `gip-inclusion/autometa`, **public** |
| App parente des review apps | `autometa-staging` (projet `service-prod/autometa`) |
| Owner des apps | `service.prod@inclusion.gouv.fr` |
| Lien SCM | établi sur `gip-inclusion/autometa`, linker `autometa-ops` |
| Auto-deploy / auto review apps | désactivés |
| Review apps existantes | aucune |
| Compte de service existant | `autometa-ops`, collaborateur de `autometa-staging` **et** de `matometa` |
| CI actuelle | `ci.yml` : lint, security, test, migrations, docker — ne déploie rien |
| Déploiements | `_deploy.yml` (push git SSH), appelé par `deploy-staging.yml` et `deploy-prod.yml` |

## Décisions

| Sujet | Décision |
|---|---|
| Autorité du cycle de vie | GitHub Actions, via l'API Scalingo. Les automatismes Scalingo restent désactivés |
| PR de forks | jamais de review app |
| Périmètre | toutes les PR internes non-draft |
| Conditionnement | déploiement seulement si lint + security + test + migrations passent |
| Destruction | à toute fermeture de PR, merge ou abandon, sans délai |
| Restitution | GitHub Deployments API |
| Identité | nouveau compte Scalingo `autometa-review`, collaborateur de `autometa-staging` uniquement |

## Architecture

```
PR ouverte / push / draft→ready          PR fermée (merge ou abandon)
        │                                        │
   ci.yml (existant)                    review-app-teardown.yml
   lint ─ security ─ test ─ migrations           │
        └──> job review-app  [needs: tous]       │
                    │                            │
        scripts/review_app.py ensure    scripts/review_app.py destroy
                    │                            │
              API Scalingo                 API Scalingo
```

Deux workflows, parce que `closed` et `opened|synchronize|reopened|ready_for_review` appellent des
travaux disjoints : relancer les tests à la fermeture d'une PR n'a pas de sens.

Le job de déploiement vit dans `ci.yml` et non dans un fichier dédié : « la CI est verte » n'existe
comme fait qu'à cet endroit, et un `needs: [lint, security, test, migrations]` l'exprime
directement. Un workflow séparé imposerait un `workflow_run`, avec son contexte de branche par
défaut et ses pièges d'autorisation, pour aucun gain.

## Réconciliation

L'état voulu est décrit, pas les transitions. Le job compare le SHA déployé au `head.sha` de la PR :

| État constaté | Action |
|---|---|
| Aucune review app pour la PR | `POST /v1/apps/autometa-staging/scm_repo_link/manual_review_app` |
| Existe, SHA déployé == `head.sha` | aucune |
| Existe, SHA déployé ≠ `head.sha` | `POST .../manual_review_app` |

Un seul endpoint sert la création et la mise à jour. L'état constaté vient de
`GET /v1/apps/autometa-staging/scm_repo_link/review_apps`, qui fournit le nom de l'app et son
dernier déploiement : le nom n'est jamais déduit d'une convention.

La convergence est la propriété qui compte. Scalingo redéploie déjà les review apps sur push via son
webhook ; si le webhook a fait le travail, on constate le bon SHA et on ne fait rien, s'il l'a raté
on rattrape. La même logique absorbe une review app supprimée à la main ou une CI relancée.

**À vérifier en premier à l'implémentation** : que `POST manual_review_app` sur une PR ayant déjà une
review app redéploie au lieu de renvoyer un conflit. Si c'est un conflit, la branche « obsolète »
bascule sur `manual_deploy` de la branche de la PR. L'architecture ne change pas.

La destruction est idempotente : review app absente vaut succès. Une PR fermée deux fois, ou déjà
nettoyée par Scalingo, ne doit pas faire échouer la CI.

## Découpage

### `scripts/review_app.py`

Deux sous-commandes, `ensure` et `destroy`. `httpx` avec timeout explicite, conformément aux règles
du dépôt. Authentification : échange du token contre un bearer court sur
`auth.scalingo.com/v1/tokens/exchange`, bearer masqué par `::add-mask::` et jamais logué.

La logique vit en Python plutôt qu'en bash dans le YAML parce que la réconciliation est exactement
la partie qui mérite des tests, et que `.claude/rules/tests.md` impose un test par modification.
`scripts/` est déjà couvert par `ruff check`.

Sortie : nom de l'app et URL sur `GITHUB_OUTPUT`, pour que le workflow publie le déploiement.

### `.github/workflows/ci.yml`

Ajout de `types: [opened, synchronize, reopened, ready_for_review]` sur le déclencheur
`pull_request`, et d'un job `review-app` conditionné à `needs`, à l'événement `pull_request`, à
l'absence de fork et à l'absence de draft.

`needs` porte sur `lint`, `security`, `test` et `migrations`, pas sur `docker` : Scalingo déploie
par buildpacks, l'image Docker ne conditionne pas le bon fonctionnement de la review app.

### `.github/workflows/review-app-teardown.yml`

Déclenché sur `pull_request: types: [closed]`. Aucun checkout du code de la PR.

### `tests/test_review_app.py`

`parametrize` sur les trois états de réconciliation, en vérifiant les appels HTTP émis. Plus la
destruction idempotente et l'absence du bearer dans les logs. Mocks via `mocker` (pytest-mock).
Aucun marqueur : le test tourne sans service ni credentials.

## Sécurité

Le contexte est celui de [SSB-2023-001](https://doc.scalingo.com/security/bulletins/ssb-2023-001)
(CVSS 8.0) : sur un dépôt public avec review apps automatiques, un fork malveillant modifiait
`scalingo.json` pour dumper les variables d'environnement et atteindre les bases. Scalingo a depuis
désactivé la création automatique depuis les forks et recommande de ne poser des review apps que sur
des applications hors production.

| Contrôle | Mise en œuvre |
|---|---|
| Forks exclus | `if: head.repo.full_name == github.repository`, **et** `--no-allow-review-apps-from-forks` côté Scalingo |
| `pull_request_target` | proscrit — c'est le vecteur d'exposition des secrets aux forks |
| Rayon d'explosion du token | compte `autometa-review`, collaborateur de `autometa-staging` et de rien d'autre |
| Stockage du secret | GitHub Environment `review-app`, distinct de `staging` et `production` |
| Permissions du job | `contents: read` + `deployments: write`. Le job de teardown ne fait aucun checkout |
| Courses concurrentes | `concurrency: review-app-pr-<N>`, pour qu'un teardown ne croise pas un déploiement |
| Actions tierces | épinglées par SHA, comme le reste du dépôt |

Les tokens API Scalingo sont liés à un compte utilisateur et n'ont **aucun scope** : un token vaut
exactement les droits de son porteur. L'isolation ne peut donc se faire que par le périmètre du
compte, ce qui est le pattern « service account » documenté par Scalingo. `autometa-ops` étant
collaborateur de `matometa`, son token donnerait à la CI un accès complet à la production — d'où le
compte dédié.

Une review app hérite des variables de `autometa-staging`, donc de vraies clés Matomo, Metabase, S3
et du token Anthropic. C'est la raison de fond pour laquelle elle reste réservée aux PR internes.
À documenter dans le README.

## Restitution

Un déploiement GitHub `review-app-pr-<N>` avec `environment_url`, passé à `inactive` au teardown.
Encart natif dans la PR, historique conservé, pas de commentaire dans la conversation. Trois appels
`gh api` dans le workflow.

## Mise en place hors code

1. Créer le compte Scalingo `autometa-review`, l'inviter uniquement sur `autometa-staging`.
2. Vérifier qu'un collaborateur non-linker peut déclencher une review app manuelle — le linker
   actuel est `autometa-ops`. Sinon, relier le SCM depuis le nouveau compte.
3. Générer son token API, le déposer dans l'Environment GitHub `review-app`.
4. Poser les réglages défensifs sur le lien SCM :
   `scalingo --app autometa-staging integration-link-update --no-deploy-review-apps --no-allow-review-apps-from-forks`

## Validation

Au-delà des tests unitaires, une PR jetable : observer création → push → mise à jour → fermeture →
destruction, et vérifier que l'encart de déploiement suit.

## Hors périmètre

- Ramasse-miettes des review apps dont la PR reste ouverte mais dormante.
- Review apps pour les contributions externes.
- Environnement dégradé sans clés d'API.

## Relecture humaine

Ce changement touche l'infrastructure de déploiement et les permissions de la CI. Il nécessite une
relecture humaine avant merge.
