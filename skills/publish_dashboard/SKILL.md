---
name: publish_dashboard
description: Publish (staging ou production), dépublier, ou lister les publications d'un tableau de bord. MUST be invoked whenever the user wants to make a dashboard public, change its public version, take a published version offline, or check what's published — garantit que le snapshot immuable, la ligne `dashboard_publications`, et le push/clear du bucket public passent TOUS par `web.publications` (jamais de S3 brut).
---

# Publish Dashboard Skill

**Point d'entrée canonique** pour publier, dépublier, ou consulter les publications d'un tableau de bord. Dès qu'un utilisateur exprime le souhait de mettre un TDB en ligne, de retirer une version, ou simplement de savoir ce qui est publié, lance ce skill **avant** toute autre action.

Ne jamais pousser des fichiers directement sur S3 et ne jamais insérer / modifier `dashboard_publications` à la main : ce skill orchestre l'ensemble du flux (snapshot immuable Autometa → push bucket public → ligne DB) et la dépublication symétrique (soft-delete + suppression bucket public, snapshot Autometa conservé pour l'audit).

## Avant de lancer

**Confirmer explicitement la cible avec l'utilisateur** :

- **Publier** : demander confirmation du `slug` ET de l'environnement (`staging` ou `production`). La production est servie sur `statistiques.inclusion.gouv.fr/dashboards/{slug}` et écrase la version prod précédente (qui passe en `unpublished_at`).
- **Dépublier** : demander confirmation du `publication_id` (court, 6 caractères). Si l'utilisateur ne le connaît pas, lancer d'abord `list --slug <slug>` et présenter les options actives.
- **Lister** : pas de confirmation nécessaire — c'est une lecture.

Ne jamais inventer un slug ou un `publication_id`. Si plusieurs publications correspondent (cas typique du staging avec plusieurs versions actives), les présenter avant de dépublier.

## Bloqueurs côté serveur

`web.publications.publish()` lève `PublicationBlocked` (code retour `1`) si :

- le TDB n'existe pas,
- il est archivé (`is_archived = true`),
- il utilise l'API query (`has_api_access` ou `has_persistence`), donc ne peut pas être servi en statique,
- le snapshot serait vide (aucun fichier sous `interactive/{slug}/`).

Ces vérifications sont systématiques et serveur — ne pas tenter de les contourner.

## Usage

```bash
# Publier en staging
.venv/bin/python skills/publish_dashboard/scripts/publish_dashboard.py publish \
    --slug mon-tdb --env staging

# Publier en production (écrase la version prod précédente)
.venv/bin/python skills/publish_dashboard/scripts/publish_dashboard.py publish \
    --slug mon-tdb --env production

# Lister les publications actives (ajouter --all pour inclure les dépubliées, audit)
.venv/bin/python skills/publish_dashboard/scripts/publish_dashboard.py list \
    --slug mon-tdb

# Dépublier une version précise
.venv/bin/python skills/publish_dashboard/scripts/publish_dashboard.py unpublish \
    --publication-id vxgbu3
```

### Sortie

JSON sur stdout. Exemple `publish` :

```json
{
  "publication_id": "vxgbu3",
  "environment": "staging",
  "published_by": "alice@inclusion.gouv.fr",
  "published_at": "2026-05-29T10:42:00+00:00",
  "url": "https://staging.statistiques.inclusion.gouv.fr/dashboards/mon-tdb-vxgbu3"
}
```

`list` renvoie un tableau JSON dans le même format. `unpublish` renvoie `{"unpublished": "<id>"}`.

## Variables d'environnement

Injectées automatiquement par `web/agents/cli.py` :

- `AUTOMETA_USER_EMAIL` — email de l'utilisateur qui publie (`published_by` dans la ligne DB).
- `AUTOMETA_CONVERSATION_ID` — loggé pour audit.

Les variables `PUBLIC_S3_BUCKET_*` et `PUBLIC_DASHBOARDS_*_URL` doivent être configurées dans l'environnement Scalingo. En dev local sans MinIO public, `publish` échouera au push vers le bucket public — c'est attendu.

## Codes de retour

- `0` — succès, JSON sur stdout.
- `1` — `PublicationBlocked` (TDB inconnu, archivé, utilise l'API query, snapshot vide), ou `publication_id` introuvable / déjà dépubliée.
- `2` — `AUTOMETA_USER_EMAIL` manquant (bug d'intégration), ou argument invalide.
