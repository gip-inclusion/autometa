# Spécification : Dashboard d'audit Tag Manager

**Branche** : `003-tm-audit-dashboard`
**Créée le** : 2026-05-02
**Statut** : Brouillon
**Reprend** : PR #34 (`louije/tm-explorer`), revue par @vperron

## Scénarios utilisateur & Tests

### User Story 1 - Audit en lecture seule des tags déployés (Priorité : P1)

Un membre de l'équipe ouvre une page web pour voir, sans se connecter à Matomo, ce qui est actuellement publié sur un site donné : quels triggers existent, quels tags se déclenchent sur quels triggers, et leurs paramètres.

**Justification** : c'est le seul usage qui motive cette PR. Tout le reste est secondaire.

**Test indépendant** : sur un site connu, le panneau triggers liste tous les triggers de la version live ; cliquer sur un trigger affiche les tags dont `fireTriggerIds` contient ce trigger.

**Scénarios d'acceptation** :

1. **Étant donné** la page `/tag-manager`, **quand** l'utilisateur clique sur un site, **alors** le panneau central liste les triggers de la version live de ce conteneur.
2. **Étant donné** un site sélectionné, **quand** l'utilisateur clique sur un trigger, **alors** le panneau de droite affiche le détail du trigger et la liste des tags qu'il déclenche.
3. **Étant donné** un site sans version publiée, **quand** l'utilisateur le sélectionne, **alors** le panneau central indique « Aucune version publiée » sans erreur.

### Cas limites

- L'API Matomo échoue (timeout, 5xx, token invalide) → message générique côté client, détail loggé côté serveur, pas de stack trace ni de secret renvoyé.
- Un site est configuré dans `sources.yaml` mais a été supprimé dans Matomo → 404 propre.
- Un trigger sans condition → indication explicite « se déclenche partout ».
- Un trigger sans aucun tag associé → message « Aucun tag déclenché par ce trigger ».

## Exigences

### Exigences fonctionnelles

- **EF-001** : La page `/tag-manager` DOIT afficher la liste des sites configurés dans `config/sources.yaml` (section `tag_manager.sites`).
- **EF-002** : La sélection d'un site DOIT charger les triggers de la **version live** du conteneur (environnement `live`), pas la draft.
- **EF-003** : La sélection d'un trigger DOIT afficher le détail de ce trigger et la liste des tags dont `fireTriggerIds` contient le `idtrigger`.
- **EF-004** : Aucune écriture (create/update/publish) n'est exposée par cette page. L'écriture reste assurée par le skill `tag_manager` côté agent.
- **EF-005** : Tous les appels Matomo passent par `lib.query.execute_matomo_query`. Aucune route ne DOIT instancier `MatomoAPI` directement.
- **EF-006** : La navigation entre panneaux utilise htmx (`hx-get`, `hx-target`). Pas de fichier JS dédié à cette page.
- **EF-007** : Sur erreur Matomo, la réponse côté client est générique (HTTP 502 + message court). Le détail est loggé en `logger.warning` avec formatage paramétré (`logger.warning("msg %s", value)`).
- **EF-008** : La page DOIT être accessible aux utilisateurs authentifiés via le même mécanisme que `/rechercher` ou `/cron` (header `X-Forwarded-Email`).

### Entités clés

- **Site Tag Manager** : `name`, `matomo_id` (int, identifiant site Matomo), `container_id` (str, identifiant conteneur TM), `staging` (bool optionnel).
- **Conteneur** : structure renvoyée par `TagManager.getContainer`, contient `draft.idcontainerversion` et `releases[]` (chacune avec `environment` et `idcontainerversion`).
- **Trigger** : `idtrigger`, `name`, `type`, `conditions[]` (chacune `actual` / `comparison` / `expected`).
- **Tag** : `idtag`, `name`, `type`, `parameters{}`, `fireTriggerIds[]`, `status`.

## Modèle de menaces

### Actifs

- Le token API Matomo (côté serveur uniquement, jamais exposé au client).
- La configuration des conteneurs (noms, IDs) — non sensibles mais internes.

### Acteurs malveillants

- Utilisateur authentifié curieux essayant d'extraire des infos via les messages d'erreur.
- Attaquant externe (en cas de fuite d'auth) cherchant à découvrir l'infrastructure via les logs ou les réponses.

### Vecteurs d'attaque & Atténuations

| # | Vecteur | Probabilité | Impact | Atténuation |
|---|---------|-------------|--------|-------------|
| 1 | Information exposure via stack trace renvoyée au client (cf. PR #34 alerte CodeQL #136) | Moy | Moy | Catcher l'erreur côté serveur, retourner un message générique, logger le détail |
| 2 | Log injection via paramètre user-controlled formaté en f-string (cf. alertes #137-138) | Moy | Bas | Formatage paramétré obligatoire (`logger.x("msg %s", val)`), validation des paramètres int via FastAPI typing |
| 3 | Accès non authentifié à la page d'audit | Basse | Bas | Dependency `get_current_user` sur chaque route |

### Risque résiduel

- Un utilisateur authentifié peut voir l'inventaire complet des tags publiés. C'est l'objectif — accepté.

## Critères de succès

- **CS-001** : Un membre de l'équipe peut, en moins de 30 secondes, identifier la liste des tags actifs sur un site donné, sans se logger sur l'UI Matomo.
- **CS-002** : 0 secret (token, URL interne complète) ou stack trace ne fuit dans les réponses HTTP en cas d'erreur Matomo.
- **CS-003** : 0 instanciation directe de `MatomoAPI` ou `MetabaseAPI` dans les routes (vérifié par test).
- **CS-004** : 0 appel `console.log` ou JS custom dans la page (vérifié par grep dans `web/static/js/`).

## Hypothèses

- Le skill `tag_manager` (déjà sur main) reste la source de vérité pour les opérations d'écriture. Cette PR ne le touche pas.
- `lib/matomo.py` expose déjà les méthodes nécessaires (`request()` GET, `post()` POST). Aucune nouvelle méthode à y ajouter.
- L'authentification est gérée en amont par le proxy (header `X-Forwarded-Email`). Pas d'auth supplémentaire à implémenter.
- Le rendu visuel de la branche `louije/tm-explorer` (template + CSS) sert de base graphique. Le JS et le code Python sont à réécrire.
- Le trafic est faible (audit interne, ~10 utilisateurs) — pas besoin de cache. Les appels Matomo sont synchrones par requête.
