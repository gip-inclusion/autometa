# Phase 1 — Quickstart : vérifier l'intégration MTM en local et en prod

**Feature** : Intégration Matomo Tag Manager sur Autometa
**Date** : 2026-04-13

## Pré-requis

- Un conteneur MTM créé dans l'instance Matomo `https://matomo.inclusion.beta.gouv.fr` (par une personne habilitée), associé au site Autometa et au moins **une fois publié** (sinon l'URL `/js/container_<ID>.js` renvoie une 404).
- L'identifiant du conteneur (ex. `abc123de`) à portée de main.

## 1. Vérifier le comportement par défaut (no-op)

Sans aucune variable d'environnement spécifique à MTM :

```bash
make dev
```

Ouvrir `http://localhost:5000`, inspecter le HTML : aucun `<script>` Matomo ne doit être présent, aucun commentaire « Matomo Tag Manager », aucun symbole `_mtm` dans la console JS. C'est le comportement attendu hors prod (EF-006).

## 2. Activer le conteneur en local

Ajouter dans `.env` :

```bash
MATOMO_TAG_MANAGER_CONTAINER_ID=abc123de
```

(Optionnellement, surcharger l'URL Matomo si besoin de pointer vers une autre instance — sinon laisser la valeur par défaut `https://matomo.inclusion.beta.gouv.fr`.)

```bash
MATOMO_URL=https://matomo.inclusion.beta.gouv.fr
```

Relancer `make dev`. Inspecter le HTML d'une page applicative (`/`, `/rechercher`, `/explorations/new`, etc.) :

- Le snippet décrit dans `contracts/template-contract.md` est présent dans `<head>`, exactement **une fois**.
- L'URL `g.src` est correctement formée : `https://matomo.inclusion.beta.gouv.fr/js/container_abc123de.js`.
- Dans l'onglet Network du navigateur, la requête vers `container_abc123de.js` retourne 200 et est `async` (non bloquante).

## 3. Vérifier l'absence sur les apps interactives

Servir une page sous `/interactive/...` (cf. `data/interactive/`). Le snippet MTM ne doit **pas** y apparaître — ces apps n'héritent pas de `base.html`.

## 4. Vérifier l'arrivée des données dans Matomo

Avec un tag « page vue » publié dans MTM et le conteneur configuré :

1. Naviguer sur quelques pages d'Autometa (`/`, `/rechercher`, etc.).
2. Ouvrir Matomo → site Autometa → **Visiteurs en temps réel** : les visites doivent apparaître en quelques secondes.
3. Si la collecte n'apparaît pas : vérifier (a) que le conteneur MTM est bien **publié** côté Matomo, (b) qu'aucune extension navigateur ne bloque le script, (c) que le tag « page vue » est activé dans la version publiée.

## 5. Tests automatisés

```bash
make test
```

Le fichier `tests/test_matomo_tag_manager.py` vérifie les deux cas (`ID set` → snippet présent ; `ID vide` → snippet absent). Les tests doivent passer sans configuration particulière (les variables sont mockées via `mocker`).

## 6. Mise en production sur Scalingo

⚠️ Penser à définir la variable côté Scalingo **en plus** du `.env` local :

```bash
scalingo -a autometa-prod env-set MATOMO_TAG_MANAGER_CONTAINER_ID=<ID_PROD>
```

Si l'instance Matomo cible est différente de la valeur par défaut, définir aussi `MATOMO_URL`. Aucune autre action côté code n'est nécessaire pour ajouter, modifier ou retirer des tags par la suite — tout se passe ensuite dans l'interface MTM.

## Critères de succès vérifiables ici

- **CS-001** : tester un échantillon de pages héritant de `base.html` et confirmer que le snippet est présent partout.
- **CS-002** : ajouter un nouveau tag dans MTM, le publier, vérifier la remontée dans Matomo en < 30 min sans toucher au code.
- **CS-003** : comparer le First Contentful Paint d'une page principale avant/après activation (DevTools → Performance) ; régression < 5 %.
