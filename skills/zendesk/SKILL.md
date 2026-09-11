---
name: zendesk
description: Zendesk du support Emplois de l'Inclusion — lire les tickets (lecture seule) et lire ou modifier la base de connaissance (Guide) avec relecture et validation avant toute écriture. (project)
---

# Zendesk

Deux périmètres sur la même instance : les **tickets** (lecture seule) et la **base de connaissance** publiée sur aide.emplois.inclusion.beta.gouv.fr (lecture et écriture encadrée).

## Configuration

Variables d'environnement (cf. `.env.example`) : `ZENDESK_SUBDOMAIN`, `ZENDESK_EMAIL`, `ZENDESK_API_TOKEN` (Admin Center → Apps → API). Instance par défaut `emplois`, définie dans `config/sources.yaml`.

```python
from lib.sources import get_zendesk

zd = get_zendesk()
```

Toutes les méthodes lèvent `ZendeskError(status_code, message)` sur erreur HTTP. Rate limit interne (~700 req/min) ; sur 429, attente de `Retry-After` et 3 réessais.

## Base de connaissance (Guide)

### Lire

| Méthode | Usage |
|---|---|
| `list_articles(section_id=None)` | Tous les articles **avec leur corps HTML** — 3 requêtes pour toute la base. C'est le chemin normal dès que la sélection dépend du contenu. |
| `get_article(id)` | Un article à l'instant T |
| `article_id_from_url(url)` | Extrait l'id d'une URL `…/hc/fr/articles/<id>-slug` |
| `search_articles(query)` | Recherche Zendesk lemmatisée et pondérée — pour un **sujet**, pas une chaîne exacte |
| `list_sections()`, `list_categories()` | Arborescence |

Pour chercher une chaîne exacte, filtrer `list_articles()` en Python (`pattern in a.body`) : exact, complet, déterministe. La recherche Zendesk renvoie des résultats approchants.

### Modifier le contenu : changeset obligatoire

Toute modification de **titre ou corps** d'un article existant passe par `lib.zendesk_changeset`, jamais par `update_article_content` en direct. Un changeset fige l'état avant et après sur S3 (`zendesk/changesets/<id>/`), produit un diff relisible, et ne s'applique qu'après validation.

```python
from lib import zendesk_changeset as cs

# Batch : rechercher-remplacer sur le titre et le texte visible du corps
result = cs.replace(zd, "Dora", "Nouveau nom")               # littéral, casse et accents comptent
result = cs.replace(zd, r"Dora( \w+)?", r"Nouveau\1", regex=True)
result = cs.replace(zd, "Dora", "Nouveau nom", include_markup=True)   # aussi liens, attributs, classes

# Modification ciblée : « regarde cette URL, ajoute ça »
article = zd.get_article(zd.article_id_from_url(url))
def transform(title, body):
    return title, body.replace("<h2>Contact</h2>", "<h2>Contact</h2>\n<p>Nouveau paragraphe.</p>")
result = cs.plan([article], transform, "ajout encart contact")

# result : {"id": "2026-09-11-1032-remplacer-dora", "articles": [...], "scanned": 229, "diff_url": ...,
#           "markup_hits": {id: n}, "structure_hits": [{"kind": "section", "id", "name"}, ...]}
# result est None si rien ne change. Un motif vide est refusé (ValueError).

cs.apply(zd, result["id"])    # → {"written": 98, "skipped": [...], "errors": [...]}
cs.revert(zd, changeset_id)   # restaure l'état d'avant, même garde
cs.show(changeset_id) ; cs.list_changesets()
```

**Ce que `replace` ne touche pas, et le dit** : les occurrences dans les balises HTML (adresses de liens, images, attributs, classes) ne sont remplacées qu'avec `include_markup=True`. Renommer Dora ne doit pas réécrire `dora.inclusion.gouv.fr`. `markup_hits` donne le compte par article : le mentionner dans la relecture, et ne passer `include_markup=True` que sur demande explicite de l'utilisateur. `structure_hits` nomme les rubriques et catégories dont le nom contient le motif : elles ne sont jamais modifiées par un changeset, proposer `update` à la main si l'utilisateur le souhaite.

**Déroulé imposé dans une conversation :**

1. Lire, construire la transformation, appeler `plan` ou `replace`. Aucune écriture Zendesk.
2. Terminer le tour par la relecture. Article seul : le diff complet dans un bloc de code. Batch : tableau des articles touchés (titre, URL, lignes modifiées), trois diffs représentatifs, le lien `diff_url`, le nombre d'articles parcourus, le mode de recherche (littéral ou expression régulière, `params`), et `markup_hits` s'il y en a. Terminer par l'identifiant du changeset et une proposition de phrase pour appliquer.
3. **Ne jamais appeler `apply` dans le tour qui a produit le `plan`.** Attendre un message de l'utilisateur qui valide explicitement — le format est libre, l'intention doit être sans ambiguïté. Si plusieurs changesets sont en jeu, l'identifiant lève le doute.
4. Après `apply`, rendre compte : écrits, sautés (« modifié entre-temps », avec titre), erreurs, et rappeler qu'un `revert` est possible avec l'identifiant.

Si l'utilisateur demande une correction à l'étape 2, produire un nouveau changeset ; l'ancien reste `planned` et n'est jamais appliqué.

**Interruption** : `apply` enregistre son avancement article par article. Si la session ou le réseau tombe, `show` donne les articles écrits et ceux qui restent (`remaining`), `apply` reprend là où il s'est arrêté, et `revert` défait ce qui a été écrit.

**Garde de cohérence** : `apply` relit chaque article et n'écrit que si son contenu est identique à l'état figé au plan ; sinon l'article est sauté et listé. `revert` fait de même contre l'état enregistré à l'application. Un article retouché à la main entre-temps n'est jamais écrasé. Pour rattraper les sautés, refaire un `plan` sur ces seuls articles (le motif d'un `replace` est dans `result["params"]`).

### Métadonnées, création, arborescence

Sans changeset, mais **toujours après confirmation en clair** dans le message précédent de l'utilisateur, en ayant décrit l'action exacte (article, section cible, champs).

```python
zd.update_article(id, section_id=…, label_names=[…], draft=False, position=…)
zd.create_article(section_id, title, body)          # brouillon par défaut ; draft=False pour publier
zd.create_section(category_id, name, description="")
zd.create_category(name, description="")
```

### Export

`cs.export_articles(zd)` dépose le dump complet gzippé (~265 Kio, 3 requêtes) sur `zendesk/exports/` et renvoie une URL présignée. À la demande uniquement : le `before` de chaque changeset est déjà la sauvegarde des articles touchés.

Le contenu des articles est public : pas d'anonymisation NIR, le HTML est réécrit tel quel.

## Tickets (lecture seule)

```python
ticket = zd.get_ticket(12345)                 # ZendeskTicket(id, subject, status, tags, ...)
comments = zd.get_ticket_comments(12345)      # [ZendeskComment(public, author_role, body, ...)]
first_reply = zd.first_user_reply(12345)      # premier message end-user après la première réponse agent
for r in zd.iter_tickets([1, 2, 3], with_comments=True):   # TicketResult(ticket, comments, error)
    ...
hits = zd.search_tickets("status:open tags:bug created>2026-01-01", sort_by="created_at", max_results=50)
n = zd.count_tickets("status:open tags:bug")
```

- `get_ticket_comments` ne lit que la première page (~100 commentaires).
- `iter_tickets(with_comments=True)` fait 2 appels par ticket ; il logue tous les 500 et continue malgré les erreurs ponctuelles.
- Les commentaires exposent `author_role` (`end-user` / `agent` / `admin`) via sideloading.

### Anonymisation des NIR (activée par défaut)

Les tickets contiennent parfois des NIR (~1,3 % sur un échantillon de 300). Le client les remplace par `[NIR-ANONYMISÉ]` dans sujets et commentaires, en validant la clé INSEE pour épargner téléphones et SIRET. Code dans `lib/pii.py` (`redact_nir`). `ZendeskAPI(..., redact=False)` désactive — jamais pour une restitution à l'utilisateur. Les autres données personnelles (nom, e-mail, téléphone) ne sont pas masquées.

## Quand l'utiliser

- Diagnostiquer une demande utilisateur (ticket #X), extraire les premières clarifications d'un échantillon, recouper tags et statuts avec Matomo ou Metabase.
- Corriger, enrichir ou renommer en masse la documentation d'aide des Emplois.
