# Un menu de filtres clair pour la recherche de conversations

## Ce que je veux

Sur la page de recherche des conversations, je veux un menu de filtres par tags
(Public, Fonctionnalité, Usage, Thème, Mesure, Source) qui soit simple à comprendre.
Aujourd'hui les catégories affichées ne correspondent plus à celles qui existent, et
les noms ne sont pas clairs. Je veux que ce soit le plus simple possible pour les
utilisateurs : de bons intitulés, seulement les catégories utiles, et des filtres
présentés comme une recherche en haut de page plutôt qu'une colonne de cases à cocher
sur le côté.

Je veux aussi que la barre de recherche cherche par le sens dans le contenu des
conversations (les « embeddings »), et pas seulement dans les titres : quand je tape des
mots, je retrouve les conversations qui parlent de ça, même sans les mots exacts.

## Ce qui devra marcher

DOD-1 — [du brief : « un menu avec filtre : avec les différents tags (audience, feature,
mesure, source, theme, usage) »] Sur la page de recherche des conversations, je peux
filtrer par chacune des catégories de tags réellement utilisées — Public, Fonctionnalité,
Usage, Thème, Mesure, Source (et Territoire s'il est utilisé) — et les anciennes catégories
qui n'affichaient plus rien (« Produit », « Type ») ont disparu.

DOD-2 — [du brief : « les noms donnés aux tags ne sont pas très clairs »] Les tags eux-mêmes
restent ceux de Notion, inchangés ; seuls deux intitulés de catégories changent pour être plus
clairs : « Public » devient **Réseau** et « Fonctionnalité » devient **Bloc fonctionnel**. Les
autres catégories gardent leur intitulé (Usage, Thème, Mesure, Source, Territoire).

DOD-3 — [du brief : « rend ça le plus simple possible » ; décision « épurer »] Une catégorie
qui n'a aucun tag posé sur les conversations affichées n'apparaît pas : je ne vois que des
filtres qui mènent à des résultats.

DOD-4 — [décision « visuel type filtre, proche de la recherche »] Les filtres sont présentés
en haut, avec la barre de recherche, sous une forme proche d'une recherche — et non dans une
colonne latérale de cases à cocher.

DOD-5 — [du brief : « rend ça le plus simple possible »] Quand je sélectionne un filtre, la
liste se restreint aussitôt aux conversations correspondantes ; quand j'en sélectionne
plusieurs, elles se combinent ; et un seul geste « Effacer » me ramène à la liste complète.

DOD-6 — [décision « sélection visible »] Je vois d'un coup d'œil quels filtres sont actifs et
combien, et ma sélection est conservée si je recharge la page ou si je navigue puis reviens.

DOD-7 — [cas limite : combinaison sans résultat] Quand mes filtres ne renvoient aucune
conversation, je vois un message clair indiquant qu'aucun résultat ne correspond, et je peux
effacer les filtres pour revenir à la liste complète.

DOD-8 — [cas limite : filtre obsolète] Un filtre conservé dans l'adresse mais qui ne
correspond plus à aucune conversation n'apparaît pas comme filtre actif : pas de filtre
« fantôme » qui donnerait une liste vide sans raison visible.

DOD-9 — [du brief : « une recherche par mots clé avec les embeddings » ; décision « sens +
repli »] Quand je tape des mots dans la barre de recherche, je retrouve les conversations dont
le contenu correspond au sens de ma recherche, même si les mots exacts ne figurent pas dans le
titre, les plus proches d'abord.

DOD-10 — [décision « repli »] Si la recherche par le sens ne trouve rien de pertinent, je
récupère quand même les conversations qui contiennent mes mots exacts, plutôt qu'une liste
vide.

DOD-11 — [du brief : « rend ça le plus simple possible »] Ma recherche par mots et mes filtres
de catégories agissent ensemble : les résultats respectent à la fois le sens de ma recherche et
les filtres actifs.

DOD-12 — [cas limite : recherche vide] Quand la barre de recherche est vide, je vois la liste
complète ordonnée par date comme aujourd'hui, sans classement par pertinence.

## Sources lues

- `web/templates/conversations.html` (R1) — menu de filtres actuel : colonne latérale de
  cases à cocher, sections `product` / `theme` / `type_demande`, barre de recherche client.
- `web/routes/html.py` — route `GET /conversations` (R1) — construction de `all_tags`,
  `active_tags`, filtrage par tags et regroupement par date.
- `lib/taxonomy.py` (R1) — facettes réelles : usage, feature, audience, theme, mesure,
  source, territoire, avec leurs libellés et l'ordre d'affichage par type d'objet.
- `web/stores/tags.py` (R1) — tags réellement utilisés par les conversations, avec comptes.
- `web/models.py` — modèle `ConversationMessageEmbedding` (R1) — vecteurs 256d (pgvector) par
  message ; infrastructure déjà en place, pas encore branchée sur la recherche.
- `web/conversation_embeddings/generate_conversation_embeddings.py`,
  `cron/generate-conversation-embeddings/cron.py` (R1) — génération des vecteurs (model2vec,
  `minishlab/potion-multilingual-128M`) : même modèle à réutiliser pour vectoriser la requête.
- `web/templates/conversations.html` — barre de recherche actuelle, filtrage texte côté
  navigateur uniquement (`filterByText`), qui ne cherche que titres et libellés de tags.
- `paved-road/notification-reponse-prete/definition-of-done.md` (R5) — format de contrat.

## Questions ouvertes

Aucune.

## Validation

Validé par Annaelle Garcia le 2026-09-23.
