---
name: attio
description: Lire le CRM Attio de l'équipe (structures, contacts, deals, listes de prospection) — chercher, filtrer, compter, sortir une liste. Lecture seule. À utiliser seulement quand la demande nomme Attio ou le CRM (suivi commercial, pipes de prospection). Pour compter ou lister des structures, voir les sources de données d'`AGENT.md`.
---

# Attio — lecteur du CRM

Accès **lecture seule** à l'API Attio (`api.attio.com/v2`) du workspace de l'équipe : objets, attributs, enregistrements et listes.

## Ce que contient le CRM

- **Objets** : `companies` (structures), `people` (contacts), `deals`, et des objets propres à l'équipe (`territoires`, `produits`, `equipes`...). `--objects` les liste.
- **Listes** : les pipes de l'équipe (acquisition, prospection, suivi des réponses). Une entrée de liste pointe vers une structure ou un contact (`parent_record_id`) et porte ses propres champs (étape, statut). `--lists` les liste.
- **Attributs utiles** :
  - `companies` : `name`, `domains`, `type_de_compte` (CCAS, Mission Locale, SIAE, Conseil Départemental...), `primary_location`, `departement_s`, `source_import` ;
  - `people` : `name`, `job_title`, `company`, `role` (Décisionnaire, Pilote), `source_import`, et un attribut par produit (`les_emplois_de_l_inclusion`, `dora`...) qui dit si la personne l'utilise (Actif / Inactif), et `statut_prospection` (attribut à choix, ajouté le 23/11/2026) : la valeur « Prospect » marque un contact de prospection pas encore approché.
- Les valeurs exactes d'un attribut à choix se lisent avec `--attributes OBJET --options ATTRIBUT` **avant** de filtrer : un libellé mal orthographié renvoie zéro résultat sans erreur.

## Données personnelles

Les contacts portent des noms et des postes. Leurs emails et leurs téléphones ne sortent jamais du connecteur, ni pour l'agent ni pour un tableau de bord. Une liste nominative ne se sort que si la demande en a besoin (relire une cible), jamais pour illustrer un comptage. Pour une analyse, donner des totaux et des répartitions. Un filtre ne porte jamais sur un email ou un téléphone, quel que soit le nom de l'attribut : un total de 0 ou 1 dirait si une personne est dans le CRM. Le connecteur refuse un tel filtre avant de l'envoyer.

## Limites

- **Lecture seule.** La clé n'a que les droits de lecture ; aucune commande n'écrit dans le CRM.
- **Pagination plafonnée.** `--count` et `--entries` lisent par pages de 500, plafonnées à 40 pages, soit 20 000 lignes. `--count` et `--entries` rendent `complete: false` quand ils atteignent ce plafond : le total ou la liste sont alors partiels, à dire comme tel. Avec `--by`, les enregistrements sans valeur sont comptés sous `null`.
- **Filtres** : syntaxe de l'API Attio. Forme courte `{"attribut": "valeur"}` pour une égalité ; forme longue pour le reste, par exemple `{"name": {"$contains": "Mission"}}` ou `{"$and": [{...}, {...}]}`.

## Commandes

```bash
# Objets du CRM, puis attributs d'un objet et valeurs d'un attribut à choix
python skills/attio/scripts/query.py --objects
python skills/attio/scripts/query.py --attributes companies
python skills/attio/scripts/query.py --attributes companies --options type_de_compte

# Chercher des enregistrements (50 par défaut, 500 au plus), en ne gardant que certains attributs
python skills/attio/scripts/query.py --search companies \
    --filter '{"type_de_compte": "Mission Locale"}' --fields name,domains,primary_location --limit 100

# Compter, avec une répartition par attribut
python skills/attio/scripts/query.py --count people --filter '{"role": "Décisionnaire"}' --by source_import

# Listes (pipes) et leurs entrées
python skills/attio/scripts/query.py --lists
python skills/attio/scripts/query.py --entries sales --fields stage
```

Sortie : JSON sur stdout. Chaque enregistrement est aplati en `{id, attribut: valeur}` ; un attribut à plusieurs valeurs rend une liste ; une référence à un autre enregistrement rend son identifiant, à relire avec `--search` sur l'objet visé.

## Dans un tableau de bord

- Dans `cron.py` : `query_attio("count", {"object": "companies", "by": "type_de_compte"})` (façade `lib.dashboard_api`).
- En direct depuis la page : `/api/query` avec `{"source": "attio", "method": "entries", "params": {"list": "sales", "fields": ["stage"]}}`. Ce mode rend le tableau non publiable (voir `docs/interactive-dashboards.md`).

Méthodes : `objects`, `attributes` (`object`), `options` (`object`, `attribute`), `records` (`object`, `filter`, `fields`, `limit`), `count` (`object`, `filter`, `by`), `lists`, `entries` (`list`, `filter`, `fields`). Un `count` sur toutes les structures prend une trentaine de secondes : dans une page, le faire dans `cron.py` plutôt qu'à l'ouverture.
