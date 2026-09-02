# API Notion

Le client du projet est `lib/notion.py`, bâti sur `httpx`. Il lit **et** écrit. Le skill
`notion` est le point d'entrée ; ne pas appeler l'API à la main ailleurs.

## Configuration

| Variable | Requise pour | Forme |
|----------|--------------|-------|
| `NOTION_TOKEN` | tout | `secret_abc...` |
| `NOTION_REPORTS_DB` | publication | identifiant de la base « Rapports publics » |

## Ce que le client sait faire

| Fonction | Rôle |
|---|---|
| `query_database(db_id)` | lister les pages d'une base, pagination comprise |
| `get_block_children(block_id)` | récupérer le contenu d'une page |
| `db_id_from_url(url)` | extraire un identifiant depuis une URL d'espace de travail |
| `publish_report(...)` | créer une page de rapport et y écrire le markdown converti |
| `is_configured()` | savoir si le jeton est présent avant de tenter un appel |

## Appels

- Base : `https://api.notion.com/v1/`
- En-tête de version : `Notion-Version: 2022-06-28`
- Authentification : `Authorization: Bearer {NOTION_TOKEN}`
- Délai d'attente : 30 s

La pagination suit `has_more` / `next_cursor`. Sur HTTP 429, respecter `Retry-After`.

## Publication de rapports

Route `POST /api/reports/{id}/publish-notion`. Crée une page dans la base « Rapports
publics » avec les propriétés `Titre`, `Date de publication`, `Produits concernés` et
`Requête initiale`, puis y ajoute le contenu.

La conversion markdown → blocs couvre titres, paragraphes, code, tableaux, listes et
séparateurs ; en ligne, gras, italique, code et liens.

## Portée de l'intégration

L'intégration ne voit que ce qui lui a été partagé explicitement. Une page absente n'est pas
manquante : elle n'est pas partagée.
