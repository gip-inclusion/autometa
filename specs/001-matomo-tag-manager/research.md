# Phase 0 — Recherche technique

**Feature** : Intégration Matomo Tag Manager sur Autometa
**Date** : 2026-04-13

Aucun marqueur `NEEDS CLARIFICATION` n'est ouvert dans le plan. Les décisions ci-dessous résolvent les choix techniques implicites pour préparer la Phase 1.

## Décision 1 — Forme du snippet injecté

- **Décision** : utiliser le snippet officiel Matomo Tag Manager fourni par l'interface MTM (chargement asynchrone via `<script>` injecté dans `<head>`, initialisation de `_mtm` et déclenchement implicite des tags configurés côté MTM). Aucune `_paq.push` ni `_mtm.push` ajoutée par le code applicatif.
- **Rationale** : c'est le seul snippet que Matomo s'engage à maintenir compatible avec les évolutions du conteneur. Tout est paramétré côté MTM, conformément à l'intention utilisateur. Toute personnalisation supplémentaire (data layer, événements applicatifs) violerait la règle « une seule fois dans le code ».
- **Alternatives écartées** :
  - *Snippet de tracking Matomo classique (`_paq`)* — écarté : oblige à coder chaque page vue/événement dans le code, exactement ce qu'on cherche à éviter.
  - *Push d'un data layer applicatif (`window._mtm = window._mtm || []; _mtm.push({...})`)* — écarté : nécessite des modifications de code à chaque nouvel événement.

## Décision 2 — Source de l'URL du serveur Matomo

- **Décision** : ajouter dans `web/config.py` une variable `MATOMO_URL` lue depuis l'environnement (valeur par défaut `https://matomo.inclusion.beta.gouv.fr` qui correspond à l'instance déjà utilisée par `config/sources.yaml`). Le snippet construit l'URL du conteneur ainsi : `{MATOMO_URL}/js/container_{ID}.js`.
- **Rationale** : centraliser la lecture des variables d'environnement dans `web/config.py` est imposé par `.claude/rules/code.md`. La valeur par défaut évite d'avoir à configurer une variable supplémentaire en prod tant que l'instance Matomo ne change pas. `config/sources.yaml` reste réservé aux clients API (avec token), pas au code de chargement frontend qui n'a besoin que d'une URL publique.
- **Alternatives écartées** :
  - *Lire l'URL depuis `lib.sources.get_source_config("matomo")`* — écarté : `lib/sources.py` est destiné aux clients API authentifiés (Matomo/Metabase) ; le faire dépendre d'un YAML pour rendre une URL publique côté HTML est une indirection inutile (« no abstractions for one usage »).
  - *Inliner l'URL dans le template* — écarté : viole `.claude/rules/code.md` (« toute lecture de variable d'environnement passe par `web/config.py` »).

## Décision 3 — Variable d'environnement

- **Décision** : `MATOMO_TAG_MANAGER_CONTAINER_ID` (chaîne, vide par défaut). Format attendu : la chaîne fournie par l'interface MTM (ex. `abc123de`). Aucune validation de format côté code (Matomo ne publie pas de schéma stable pour ces IDs).
- **Rationale** : nom long mais explicite, sans collision avec `MATOMO_API_KEY` déjà existant (clairement distinct). Comportement no-op si vide → comportement souhaité hors prod (cf. clarification Q1 de la spec).
- **Alternatives écartées** :
  - *`MATOMO_CONTAINER_ID`* — moins explicite, on pourrait croire qu'il s'agit d'un ID d'instance Matomo plutôt que d'un conteneur MTM.
  - *Activation par un booléen `MATOMO_TAG_MANAGER_ENABLED`* — écarté : doublonne avec la présence/absence de l'ID. Une seule variable suffit.

## Décision 4 — Point d'injection dans le template

- **Décision** : injecter le snippet dans `<head>` de `web/templates/base.html`, juste avant `{% block head %}{% endblock %}`. Le bloc Jinja entier est conditionné par `{% if matomo_tag_manager_container_id %}`.
- **Rationale** : Matomo recommande l'injection en `<head>` (le plus tôt possible, avant les autres scripts) pour ne pas manquer les premiers événements. Position avant `{% block head %}` permet à un template enfant de surcharger ou compléter le `<head>` sans court-circuiter l'injection.
- **Alternatives écartées** :
  - *Fin de `<body>`* — écarté : retarde la disponibilité de MTM, peut faire manquer des événements précoces. Va à l'encontre de la doc Matomo officielle.
  - *Fichier de template séparé `_matomo_tag_manager.html` inclus via `{% include %}`* — écarté : un seul `if`/`script` de quelques lignes ne justifie pas un fichier dédié (« pas d'abstraction pour un seul usage », `.claude/rules/code.md`).

## Décision 5 — Exposition aux templates

- **Décision** : exposer `matomo_tag_manager_container_id` et `matomo_url` comme `templates.env.globals` dans `web/deps.py`, à côté de `static_url` et `format_relative_date`.
- **Rationale** : pattern déjà en place dans `web/deps.py`. Évite d'avoir à passer ces variables à chaque appel `templates.TemplateResponse(...)` dans les routes (il y en a beaucoup), et garantit que le snippet sera disponible sur 100 % des pages héritant de `base.html` sans risque d'oubli (CS-001).
- **Alternatives écartées** :
  - *Passer les valeurs via chaque `TemplateResponse`* — écarté : bruyant, fragile (oubli possible sur une nouvelle route → page sans tracking).
  - *Context processor FastAPI dédié* — écarté : `templates.env.globals` est plus simple et déjà utilisé dans le projet (pas de pattern divergent à introduire).

## Décision 6 — Tests

- **Décision** : un test pytest qui rend `base.html` deux fois — une fois avec un ID positionné dans `templates.env.globals`, une fois avec une chaîne vide — et asserte la présence/absence du snippet. Utilise la fixture `mocker` de pytest-mock pour patcher temporairement les globals Jinja. Pas de test d'intégration HTTP réel (le rendu Jinja suffit).
- **Rationale** : couvre les deux scénarios critiques (présent en prod, absent en dev par défaut) avec un coût minimal. Conforme à `.claude/rules/tests.md` (pytest only, mocker depuis pytest-mock, paramétrage si besoin).
- **Alternatives écartées** :
  - *Test d'intégration via TestClient FastAPI* — écarté : ajoute du couplage à l'app entière pour vérifier deux lignes de template ; le rendu Jinja direct est plus rapide et plus ciblé.
