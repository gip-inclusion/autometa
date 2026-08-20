# Review apps pilotées par la CI — design

Date : 2026-08-11 (mis à jour 2026-08-12 avec les vérifications sur l'infrastructure)
Statut : validé, prérequis d'infrastructure en place, prêt pour le plan d'implémentation

## Problème

Les review apps Scalingo existent (`scalingo.json` seed `AUTOMETA_ENV=review` et
`OAUTH2_PROXY_REDIRECT_URL` sur le domaine de la PR) mais se déclenchent à la main depuis le
dashboard Scalingo. Rien ne les crée, ne les met à jour ni ne les supprime automatiquement, et leur
existence n'est corrélée à aucun état de la pull request.

On veut un cycle de vie lié à la PR : création à l'ouverture, mise à jour quand le code change,
destruction à la fermeture — le tout décidé par la CI, sur un dépôt public, sans exposer les
identifiants de production.

## État constaté

| Élément | Valeur |
|---|---|
| Dépôt | `gip-inclusion/autometa`, **public** |
| App parente des review apps | `autometa-staging` (projet `service-prod/autometa`) |
| Owner des apps | `service.prod@inclusion.gouv.fr` |
| Lien SCM | établi le 2026-06-23, linker `autometa-ops`, branche `main` |
| Review apps existantes | aucune |
| CI actuelle | `ci.yml` : lint, security, test, migrations, docker — ne déploie rien |
| Déploiements | `_deploy.yml` (push git SSH), appelé par `deploy-staging.yml` et `deploy-prod.yml` |
| `matometa` | **aucun lien SCM** — la production se déploie uniquement par push SSH |

Réglages du lien SCM, tous déjà dans l'état voulu :

| Réglage | Valeur |
|---|---|
| `auto_deploy_enabled` | `false` |
| `deploy_review_apps_enabled` | `false` |
| `automatic_creation_from_forks_allowed` | `false` |
| `delete_on_close_enabled` | `true` |
| `hours_before_delete_on_close` | `0` |
| `delete_stale_enabled` | `true` |
| `hours_before_delete_stale` | `72` |

Ces valeurs constituent l'invariant sur lequel repose le design : Scalingo ne crée aucune review app
de lui-même, et n'en crée en particulier jamais depuis un fork. Aucune commande n'est nécessaire
pour les poser, mais toute bascule depuis le dashboard invaliderait l'hypothèse d'autorité unique.

`delete_on_close_enabled: true` signifie que Scalingo détruit déjà les review apps à la fermeture des
PR, sans délai. Le workflow de teardown ne porte donc pas la destruction elle-même : il porte le
déterminisme (ne pas dépendre d'un réglage tiers), la visibilité dans la CI, et le passage du
déploiement GitHub à `inactive`, que Scalingo ne fera jamais.

## Décisions

| Sujet | Décision |
|---|---|
| Autorité du cycle de vie | GitHub Actions, via l'API Scalingo. Les automatismes Scalingo restent désactivés |
| PR de forks | jamais de review app |
| Périmètre | toutes les PR internes non-draft |
| Conditionnement | déploiement seulement si lint + security + test + migrations passent |
| Destruction | jamais par la CI : Scalingo détruit à la fermeture et après 72 h sans déploiement |
| Passage en draft | la CI éteint l'app (`web` à zéro), Scalingo ne réagissant pas à cet événement |
| Restitution | GitHub Deployments API |
| Identité | compte Scalingo dédié `reviewapp.autometa@inclusion.gouv.fr` |

## Architecture

```
PR ouverte / push / draft→ready          PR fermée (merge ou abandon)
        │                                        │
   ci.yml (existant)                    review-app-teardown.yml
   lint ─ security ─ test ─ migrations      closed ──> job deactivate
        └──> job review-app  [needs: tous]  draft  ──> job stop
                    │                            │
        scripts/review_app.py ensure     scripts/review_app.py stop
                    │                     (sur draft seulement)
              API Scalingo
```

À la fermeture, Scalingo détruit l'app de lui-même : il ne reste qu'à éteindre l'encart de la PR,
sans checkout, sans Python et sans token Scalingo.

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
| Aucune review app pour la PR | créer, attendre les addons, puis déployer |
| Existe, dernier déploiement en `success` sur `head.sha` | aucune |
| Existe, tout autre cas | déployer |

Deux endpoints, pas un seul. `POST /v1/apps/autometa-staging/scm_repo_link/manual_review_app` crée
l'app et provisionne ses addons, **sans jamais la déployer** : elle reste en `status: "new"`. Le
déploiement vient de `POST /v1/apps/{review_app}/scm_repo_link/manual_deploy`, avec la branche de la
PR. Un second `manual_review_app` sur une review app existante renvoie un `HTTP 500 — name has
already been taken`, il ne sert donc jamais à mettre à jour.

Entre les deux, il faut attendre que les addons passent `running` : l'addon PostgreSQL met une
soixantaine de secondes, et `DATABASE_URL` n'existe qu'à ce moment-là. Déployer avant, c'est un
postdeploy qui meurt sur une URL de base vide.

L'état constaté vient de `GET /v1/apps/autometa-staging/scm_repo_link/review_apps`, qui fournit le
nom de l'app et son dernier déploiement. Le nom vient de l'API : la review app listée d'abord, sinon
le corps de la réponse au `POST` de création, sous `review_app.app_name`.

Un déploiement qui n'est pas en `success` ne compte pas comme déployé : une app morte en
`hook-error` sur le bon SHA doit être redéployée, pas déclarée à jour.

`ensure` attend la fin du build avant de rendre la main. L'API répond en moins d'une seconde avec un
déploiement `queued`, alors que le build dure environ deux minutes : sans cette attente, la CI
publierait un déploiement GitHub `success` pointant vers une URL qui ne répond pas encore, et un
`hook-error` — le mode d'échec le plus courant sur une app neuve — passerait entièrement inaperçu.
Le coût est de deux à trois minutes de runner par déploiement, gratuites sur un dépôt public.

La convergence est la propriété qui compte. `deploy_review_apps_enabled` est à `false`, donc rien ne
redéploie de lui-même et c'est toujours la CI qui agit. En contrepartie, la même logique absorbe sans
rien savoir une review app détruite par `delete_stale_enabled`, supprimée à la main, ou une CI
relancée : elle constate, et elle ramène à l'état voulu.

La CI ne détruit jamais. Le compte qu'elle utilise est collaborateur de `autometa-staging`, et
Scalingo réserve la suppression au propriétaire — un `DELETE` répond `401`. Trois mécanismes s'en
chargent à sa place, tous côté Scalingo :

- `delete_on_close_enabled` à la fermeture de la PR, sans délai ;
- `delete_stale_enabled` après 72 h sans déploiement, le compteur repartant à chaque déploiement ;
- rien au passage en draft, où Scalingo ne réagit pas : la CI éteint alors l'app avec
  `POST /v1/apps/{review_app}/scale` et `web` à zéro, ce qu'un collaborateur a le droit de faire.

Ces deux réglages portent donc à eux seuls la garantie que rien ne fuit. `ensure` lit le lien SCM à
chaque exécution et échoue si `delete_on_close_enabled` est repassé à `false`, pour qu'une bascule
depuis le dashboard se voie en rouge au lieu de passer inaperçue.

## Découpage

### `scripts/review_app.py`

Deux sous-commandes, `ensure` et `stop`. `httpx` avec timeout explicite, conformément aux règles
du dépôt. Authentification : échange du token contre un bearer court sur
`auth.scalingo.com/v1/tokens/exchange`. Le bearer ne quitte jamais le processus — il n'est ni écrit
sur la sortie standard ni exporté vers le workflow, ce qu'un test vérifie
(`test_main_ensure_prints_json_and_never_leaks_the_bearer`). Garantie plus forte qu'un masquage par
`::add-mask::`, qui ne fait que caviarder après coup ce qui a déjà été écrit.

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

Le checkout se fait sur `github.event.pull_request.base.sha`, **pas** sur le head. Le job n'a besoin
que du numéro de PR pour appeler l'API, jamais du code de la PR. C'est de la défense en profondeur
contre une modification accidentelle de `scripts/review_app.py`, pas une frontière de sécurité :
voir la section Sécurité, qui explique pourquoi.

### `.github/workflows/review-app-teardown.yml`

Déclenché sur `pull_request: types: [closed, converted_to_draft]`, avec un job par événement parce
qu'ils n'ont presque rien en commun.

Le job `stop` ne tourne qu'au passage en draft. Il éteint la review app, donc il a besoin du script,
donc d'un checkout de `base.ref` — la branche de destination, jamais le head de la PR, qui peut
d'ailleurs avoir déjà disparu.

Le job `deactivate` ne tourne qu'à la fermeture. Scalingo ayant déjà détruit l'app, il ne fait plus
que passer les déploiements GitHub à `inactive` : ni checkout, ni Python, ni accès au secret
Scalingo. C'est du `gh api`, préinstallé sur le runner.

### `tests/test_review_app.py`

`parametrize` sur les états de réconciliation, en vérifiant la séquence exacte des appels HTTP
émis — c'est elle qui porte le sens, puisque créer et déployer sont deux appels distincts. Plus
l'extinction, l'attente des addons, et l'absence du bearer dans les logs.

Les chemins d'échec sont testés autant que les chemins nominaux : un `FakeClient` qui fait toujours
réussir encode les hypothèses au lieu de les éprouver, et c'est ce qui avait laissé passer le `500`
de `manual_review_app`. Le double factice sait donc renvoyer `500` et `401`.

Doubles écrits à la main pour la couche HTTP (`FakeClient`, `FakeResponse`), `mocker` (pytest-mock)
pour le reste. Aucun marqueur : le test tourne sans service ni credentials.

## Sécurité

Le contexte est celui de [SSB-2023-001](https://doc.scalingo.com/security/bulletins/ssb-2023-001)
(CVSS 8.0) : sur un dépôt public avec review apps automatiques, un fork malveillant modifiait
`scalingo.json` pour dumper les variables d'environnement et atteindre les bases. Scalingo a depuis
désactivé la création automatique depuis les forks et recommande de ne poser des review apps que sur
des applications hors production.

| Contrôle | Mise en œuvre |
|---|---|
| Forks exclus | `if: head.repo.full_name == github.repository`, et `automatic_creation_from_forks_allowed: false` côté Scalingo |
| `pull_request_target` | proscrit — c'est le vecteur d'exposition des secrets aux forks |
| Code non relu | checkout sur `base.sha` (teardown : `base.ref`), jamais sur le head de la PR — défense en profondeur, pas frontière : cf. ci-dessous |
| Rayon d'explosion du token | compte `reviewapp.autometa`, collaborateur de `autometa-staging` et de rien d'autre — vérifié |
| Stockage du secret | `SCALINGO_REVIEW_APP_TOKEN` dans l'Environment GitHub `review-app` |
| Permissions du job | `contents: read`, `deployments: write`, `pull-requests: read` pour relire l'état vivant de la PR |
| Courses concurrentes | `concurrency: review-app-pr-<N>`, pour qu'un teardown ne croise pas un déploiement. Le groupe n'est rejoint qu'une fois le job prêt : le job relit donc l'état vivant de la PR et ne crée rien si elle n'est plus ouverte |
| Actions tierces | épinglées par SHA, comme le reste du dépôt |

Ce que le checkout sur `base.sha` ne protège pas : sur un événement `pull_request`, GitHub exécute la
**définition du workflow telle qu'elle est dans la PR**. Une PR interne peut supprimer la ligne
`ref:`, ou ajouter une étape qui affiche le secret, sans toucher une ligne de
`scripts/review_app.py`. Le checkout sur la base est une défense en profondeur contre une
modification accidentelle ou distraite du script, pas une frontière de sécurité.

La frontière réelle tient en trois choses : l'exclusion des forks, le droit de push sur
`gip-inclusion/autometa`, et les règles de protection portées par l'Environment `review-app`.
Autrement dit, **quiconque a le droit de pousser sur le dépôt peut obtenir ce token**. C'est une
posture défendable — le token ne voit que `autometa-staging`, et le rayon d'explosion est celui d'un
environnement hors production — mais elle doit être écrite plutôt que sous-entendue.

Les tokens API Scalingo sont liés à un compte utilisateur et n'ont **aucun scope** : un token vaut
exactement les droits de son porteur. L'isolation ne peut donc se faire que par le périmètre du
compte, ce qui est le pattern « service account » documenté par Scalingo.

Le secret s'appelle `SCALINGO_REVIEW_APP_TOKEN` et non `SCALINGO_API_TOKEN` délibérément. Un secret
`SCALINGO_API_TOKEN` orphelin existe au niveau dépôt ; un nom distinct garantit qu'un job ayant omis
sa clé `environment:` échoue bruyamment sur un secret vide, au lieu de récupérer silencieusement un
credential dont on ignore le porteur.

### Constats connexes, hors périmètre

- `SCALINGO_API_TOKEN` et `DEPLOY_SSH_KEY` sont des secrets de niveau dépôt qu'aucun workflow
  n'utilise. Porteur inconnu. À auditer et probablement à révoquer.
- `SCALINGO_SSH_KEY`, qui déploie la production, est également de niveau dépôt : lisible par
  n'importe quel job de n'importe quelle branche interne. Les Environments `staging` et `production`
  existent mais n'ont ni secret, ni règle de protection, ni politique de branche — la clé
  `environment:` de `_deploy.yml` n'a donc aujourd'hui aucun effet de cloisonnement.

## Dépendance à documenter

L'autorisation GitHub est portée par le lien SCM de l'application, pas par le compte qui l'utilise :
n'importe quel collaborateur emprunte les identifiants du lien. Toute la chaîne repose donc sur
l'autorisation OAuth d'`autometa-ops`. S'il quitte le dépôt ou révoque cette autorisation, les
review apps cassent — pour tout le monde, quel que soit le compte appelant.

## Restitution

Un déploiement GitHub `review-app-pr-<N>` avec `environment_url`, passé à `inactive` au teardown.
Encart natif dans la PR, historique conservé, pas de commentaire dans la conversation. Trois appels
`gh api` dans le workflow.

## Vérifications effectuées (2026-08-12)

| Vérification | Résultat |
|---|---|
| Échange token → bearer sur `auth.scalingo.com` | fonctionne |
| Compte porteur du token | `reviewapp.autometa@inclusion.gouv.fr` |
| Applications visibles par ce token | `autometa-staging` seule — isolation effective |
| Lecture `scm_repo_link` et `review_apps` | 200 |
| Écriture `manual_review_app` par un collaborateur non-linker | **autorisée** — l'appel n'a échoué que sur une PR fictive, en 400 côté GitHub et non en 403 côté Scalingo |

Cette dernière ligne clôt la question laissée ouverte à la conception : le compte dédié n'a besoin
d'aucune intégration GitHub propre.

## Sondage de bout en bout (2026-08-18)

Deux pull requests jetables (#195, #196), créées, déployées, passées en draft, éteintes et fermées,
avec le token de `reviewapp.autometa`. Tout ce qui suit est mesuré, pas supposé.

| Appel | Résultat |
|---|---|
| `POST manual_review_app` | `200` en 17 s. Crée l'app et provisionne ses addons, **sans la déployer** : `status: "new"`, zéro déploiement |
| Provisionnement de l'addon PostgreSQL | ~63 s. `DATABASE_URL` n'apparaît qu'une fois l'addon `running` |
| `POST {review_app}/scm_repo_link/manual_deploy` | `200`. Build ~2 min, postdeploy compris |
| `POST manual_review_app` une seconde fois | `500 — create app: * name → has already been taken` |
| Passage de la PR en draft | aucune réaction de Scalingo, la review app reste debout et saine |
| `POST {review_app}/scale` avec `web: 0` | `202` |
| `DELETE {review_app}` | `401` |
| Fermeture de la PR | app détruite en moins de 20 s |
| `delete_stale`, testé à 1 h | destruction automatique confirmée, addon compris |

Trois précisions qui ne se devinent pas :

- `stale_deletion_date` **se réinitialise à chaque déploiement** : le seuil compte les heures sans
  déploiement, pas depuis la création.
- La péremption n'est pas ponctuelle. Scalingo balaie périodiquement : échéance à 10:37 UTC,
  destruction effective vers 11:00. Sans conséquence à 72 h, ça en aurait eu à un seuil court.
- Le compte `reviewapp.autometa` est collaborateur, comme les six autres comptes humains ;
  `service.prod@inclusion.gouv.fr` est le seul propriétaire. Aucun token provisionnable ne pourra
  donc supprimer une review app.

Les trois hypothèses restées ouvertes sont tranchées : `last_deployment.git_ref` **est** le SHA
complet sur 40 caractères, le nom suit bien `autometa-staging-pr<N>`, et `manual_review_app` ne
redéploie pas.

## Mise en place hors code

Fait :

1. Alias `reviewapp.autometa@inclusion.gouv.fr`, redirigé vers `ops.autometa@`, lui-même redistribué
   à trois personnes.
2. Compte Scalingo créé, invitation sur `autometa-staging` acceptée, rôle collaborateur non limité.
3. Token API généré depuis ce compte.
4. Environment GitHub `review-app` créé, secret `SCALINGO_REVIEW_APP_TOKEN` déposé.

Reste :

5. Régénérer le token et remplacer le secret une fois la chaîne validée de bout en bout : le token
   initial a transité en clair hors d'un canal sécurisé.
6. Facultatif : renommer le username Scalingo en `autometa-reviewapp` pour suivre la convention
   `autometa-<rôle>`. Sans effet — les droits sont attachés au `user_id`.

## Validation

Au-delà des tests unitaires, une PR jetable : observer création → push → mise à jour → fermeture →
destruction, et vérifier que l'encart de déploiement suit.

## Hors périmètre

- Ramasse-miettes des review apps dont la PR reste ouverte mais dormante.
- Review apps pour les contributions externes.
- Environnement dégradé sans clés d'API.
- Cloisonnement des secrets existants (`SCALINGO_SSH_KEY`) dans leurs Environments.

## Relecture humaine

Ce changement touche l'infrastructure de déploiement et les permissions de la CI. Il nécessite une
relecture humaine avant merge.
