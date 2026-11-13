---
name: notion
description: Lire et écrire dans Notion — interroger une base de données ou une page, et publier des rapports. À utiliser dès qu'une demande référence une page/base Notion (URL app.notion.com, ou ancien notion.so).
---

# Notion

> Avant d'écrire : relire chaque chiffre contre les sorties d'outil, et poser la question si la cible est ambiguë (`AGENT.md`, « Chiffres et affirmations »).

Client unique pour l'API Notion : `lib.notion` (lecture + écriture), ses fonctions et, pour tout autre endpoint, `notion.notion_request` (voir « Autres endpoints »). Jamais de client httpx ad hoc ni de `NOTION_TOKEN` lu à la main.

**Ne jamais `WebFetch` une URL Notion** (`app.notion.com`, ou ancien `notion.so`) : l'app web est authentifiée et rendue en JS, on ne récupère qu'un écran de connexion. Toujours passer par l'API via `lib.notion`.

## Lire une base de données

Une URL de base de données ressemble à `https://app.notion.com/<workspace>/<db_id>?v=<view_id>`. Extraire l'id (le `?v=...` est l'id de **vue**, à ignorer), puis interroger :

```python
from lib import notion

db_id = notion.db_id_from_url("https://app.notion.com/gip-inclusion/1455f321b60480f68fb4fbab8ad1a6e9?v=...")
pages = notion.query_database(db_id)          # toutes les lignes (paginé)
rows = [notion.extract_page_properties(p) for p in pages]
# rows = [{"type de donnée": "...", "habilitations": [...], ...}, ...]
```

`extract_page_properties` aplatit chaque ligne en `dict` Python : `title`/`rich_text` → str, `select` → str, `multi_select`/`relation`/`people` → list, `date` → str ISO.

Une base à plusieurs sources de données (`400` « Databases with multiple data sources are not supported in this API version ») se lit source par source, avec les mêmes `filter` et `sorts` :

```python
for source in notion.data_sources(db_id):    # [{"id": ..., "name": ...}]
    pages = notion.query_data_source(source["id"])
```

## Lire le contenu d'une page

```python
from lib import notion

blocks = notion.get_block_children(page_id)   # récursif, paginé
text = "\n".join(notion.extract_block_text(b) for b in blocks)
```

## Autres endpoints

`notion.notion_request(method, endpoint, payload=None, version=...)` est le point d'entrée générique : il couvre tout endpoint que le module n'enveloppe pas (jeton, version d'API, reprise sur 429 inclus) :

```python
page = notion.notion_request("GET", f"pages/{page_id}")
props = notion.extract_page_properties(page)
hits = notion.notion_request("POST", "search", {"query": "OKR", "page_size": 20})["results"]
schema = notion.notion_request("GET", f"data_sources/{source_id}", version=notion.DATA_SOURCES_VERSION)
```

La version par défaut est celle de 2022 ; les endpoints apparus avec les sources de données (`data_sources/…`) demandent `version=notion.DATA_SOURCES_VERSION`.

## Publier un rapport

```python
from lib import notion

page_id, url = notion.publish_report(title="...", content=markdown, website="emplois")
```

Publie dans la base « Rapports publics » (`NOTION_REPORTS_DB`). Préférer le skill `save_report` pour le flux applicatif standard.

## Prérequis d'accès (important)

`NOTION_TOKEN` est l'intégration de publication des rapports. **Elle ne peut lire une page/base que si celle-ci lui a été partagée** dans Notion (menu ⋯ → Connexions). Sinon l'API renvoie `404`/`object_not_found`, quel que soit le code. Si une lecture échoue en 404, demander que la page soit partagée avec l'intégration.

Un `400` « does not contain any data sources accessible by this API bot » sur une base, ou `data_sources` vide, signifie que ce bloc est une **vue liée** à une base rangée ailleurs, non partagée avec l'intégration. Ce n'est pas une limite du client : demander l'URL de la base d'origine ou son partage.
