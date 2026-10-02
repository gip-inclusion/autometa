# Lentille design-coherence — 2026-10-02

Deux passes en parallèle (Fable, Opus). Un bloqueur (Fable), quatorze remarques à elles deux, dont
plusieurs communes. Ce qui en a été fait :

- **Bloqueur, DOD-2 : valeur d'action en liste (champ à choix multiples) fait planter la fiche** —
  corrigé : chaque valeur est traduite par les options du champ, une liste reste une liste ; une
  action inconnue à valeur liste (`side_conversation_slack`, présente une fois en production) est
  rendue telle quelle. Vérifié sur les 322 macros réelles : aucun champ personnalisé à valeur liste
  aujourd'hui, une seule action à valeur liste.
- **Valeur liste dans le texte remplacé (`comment_value` au format `["channel:all", "…"]`)** —
  corrigé par retrait : `comment_value` n'est plus un champ texte du remplacement. Aucune macro n'en
  porte (304 `comment_value_html`, 0 `comment_value`). Règle aussi la remarque sur le diff d'une
  réponse en texte brut non découpée.
- **Une transformation peut renvoyer une clé hors des quatre champs (restriction), écrite sans être
  montrée ni défaite** — corrigé : `plan_items` refuse une transformation qui ne rend pas exactement
  les champs éditables. Le skill dit que la restriction ne passe pas par un changeset.
- **`create_macro(active=True)` contredit DOD-10** — corrigé : le paramètre est retiré, une macro
  naît toujours inactive.
- **`replace_tag` dédoublonnait aussi les étiquettes voisines** — corrigé : seule la nouvelle
  étiquette est dédoublonnée.
- **`describe` sur une macro lue seule n'avait pas l'usage sur 30 jours** — corrigé : `get_macro`
  demande `usage_30d`.
- **Garde : la liste, la lecture unitaire et la réponse du `PUT` doivent donner la même
  représentation** — vérifié le 2026-10-02 sur les 322 macros : liste et lecture unitaire sont
  identiques champ à champ. L'aller-retour `PUT` (macro jetable inactive créée, remplacement appliqué
  puis défait, comparée à l'identique, supprimée) a passé le 2026-10-02 contre le Zendesk de
  production, avec l'accord du demandeur ; aucune macro de test ne reste.
- **`description: null` (5 macros) réécrite en `""` à l'application** — conservé : invisible, la
  lecture normalise les deux en `""`, la garde compare des valeurs normalisées.
- **Une entité HTML contenant le motif est remplacée dedans (« 39 » dans `&#39;`)** — conservé :
  protéger les entités comme des balises empêcherait DOD-20 (une espace insécable codée doit
  correspondre à une espace). Le cas exige un motif qui soit un nombre ou un nom d'entité (`nbsp`,
  `quot`, `amp`) ; le diff le montre ligne à ligne avant approbation.
- **Le manifeste d'un changeset de macros range les macros sous la clé `articles`** — conservé pour
  ne pas rompre la lecture des changesets d'articles déjà sur S3 ; `kind` lève l'ambiguïté et le skill
  le dit.
- **`lines_changed` compte désormais un titre modifié, articles compris** — conservé : un article dont
  seul le titre change affichait 0 ligne modifiée, ce qui le rendait invisible dans le tableau de
  relecture.
- **Une écriture dont l'accusé s'est perdu apparaît encore comme restante avant reprise** — conservé,
  identique au précédent ; la reprise suivante la classe.
- **`category` retire les espaces autour du segment** — conservé : « ` Prolongation ` » et
  « `Prolongation` » désignent la même catégorie dans le menu des agents, et la comparaison reste
  exacte sur le texte.
- **Excès sans critère** (`priority`, `type` dans les libellés, `&`, `<`, `>` dans les équivalences
  d'affichage) — conservé : coût nul, même règle que les espaces et guillemets de DOD-20.

Seconde passe (Fable), 2026-10-02 : aucun bloqueur. Deux remarques traitées : `markup_hits` n'est
plus annoncé quand `include_markup=True` remplace justement ces occurrences ; l'aller-retour réel est
consigné ci-dessus. Troisième remarque conservée : le test réel supprime sa macro jetable par l'API
brute, seul chemin de suppression du dépôt, réservé au nettoyage du test comme pour les articles.
