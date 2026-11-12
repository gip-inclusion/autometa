# Taguer et trier les jobs

## Ce que je veux

Sur la page `/jobs`, ranger les pipelines du moteur de jobs avec des tags, dont « agent », pour
retrouver d'un coup d'œil les agents parmi les autres jobs, et trier la liste autrement que par la
seule activité récente.

## Ce qui devra marcher

DOD-1 — Quand je coche un tag dans l'éditeur d'un pipeline, sur `/jobs/pipelines/<id>`, alors le
  pipeline porte ce tag : il apparaît sur le pipeline dans la liste et reste coché au rechargement.

DOD-2 — Quand je décoche un tag porté par un pipeline, alors le pipeline ne le porte plus.

DOD-3 — Le terme « agent » est disponible dès le déploiement, sans synchro Notion. Depuis l'éditeur
  d'un pipeline, je peux créer un nouveau terme de la facette « Nature » (par exemple « veille ») :
  il est posé sur le pipeline et marqué « proposé », comme un terme créé depuis un tableau de bord.

DOD-4 — `/jobs?tag=agent` ne liste que les pipelines tagués « agent ». Avec plusieurs tags, un
  pipeline doit les porter tous. Un tag que personne ne porte donne une liste vide, avec un message
  qui le dit. Le filtre actif reste appliqué quand j'ouvre un pipeline de la liste.

DOD-5 — La liste se trie par activité récente (date du dernier run, défaut actuel inchangé), par
  nom, ou par tag (les pipelines regroupés par leur premier tag, les non tagués à la fin). Une valeur
  de tri inconnue retombe sur le défaut.

DOD-6 — Toute personne connectée peut taguer un pipeline, comme elle peut déjà le lancer. Taguer un
  pipeline que le service de jobs ne connaît pas répond 404, et un service de jobs indisponible
  répond 502 : dans les deux cas, rien n'est écrit.

DOD-7 — La synchro du vocabulaire depuis Notion ne supprime jamais un terme porté par un job : elle
  le désactive, comme pour un tableau de bord, une conversation ou un rapport.

DOD-8 — La page `/jobs` affiche les tags de chaque pipeline dans la liste, une barre de filtres avec
  le nombre de pipelines par tag, le choix du tri, et l'éditeur de tags du pipeline sélectionné.

## Sources lues

- `lib/jobs.py`, `web/routes/jobs.py` : le client du service de jobs ne sait que créer et lister
  des pipelines ; aucune route de mise à jour, aucun champ de métadonnées éditable. Les tags vivent
  donc côté Autometa, dans une table de liaison `job_tags` (identifiant de pipeline, tag), sans clé
  étrangère vers le pipeline qui vit ailleurs.
- `web/models.py`, `web/stores/tags.py`, `lib/taxonomy.py`, `web/routes/dashboards.py`,
  `lib/tag_sync.py` : le système de tags de #190 (vocabulaire unique `tags`, facettes, implications,
  termes proposés, synchro Notion) sert déjà les conversations, les rapports et les tableaux de
  bord par une table de liaison chacun. Les jobs en deviennent le quatrième porteur, plutôt qu'un
  second système. D'où `DOD-7` : sans l'ajout de `job_tags` aux assignations, la synchro Notion
  supprimerait un terme porté par un job seul.
- `web/deps.py:get_current_user`, `scripts/check_route_auth.py` : les routes neuves portent la
  dépendance d'authentification ; la baseline de `gates.toml` n'est pas étendue.

## Questions ouvertes

Aucune.

## Validation

En attente de validation par Alexis Akinyemi. Défauts retenus : tags côté Autometa (table
`job_tags` sur le vocabulaire `tags`), nouvelle facette « Nature » réservée aux jobs avec « agent »
semé comme terme proposé, facettes offertes sur un job : Nature, Fonctionnalité, Thème, Territoire ;
toute personne connectée peut taguer ; tris : activité récente (défaut), nom, tag.
