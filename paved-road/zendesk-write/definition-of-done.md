# Modifier la base de connaissance Zendesk depuis Autometa

## Ce que je veux

Pouvoir demander à Autometa de corriger, enrichir ou renommer en masse les articles de l'aide en
ligne des Emplois (aide.emplois.inclusion.beta.gouv.fr), sans passer par l'interface Zendesk.
Une petite retouche sur une page comme un rechercher-remplacer sur cent pages doivent être
possibles, mais rien ne doit s'écrire sans que j'aie vu et validé ce qui va changer, et je dois
pouvoir revenir en arrière.

## Ce qui devra marcher

DOD-1 — [du brief : « rechercher-remplacer le nom d'un produit »] Quand je demande de remplacer
  un mot ou une expression dans toute l'aide, Autometa me présente la liste des articles qui
  changeraient, brouillons compris, avec pour chacun ce qui est retiré et ce qui est ajouté, et
  rien n'est encore modifié dans Zendesk.

DOD-2 — [du brief : « regarde cette URL, ajoute ça »] Quand je donne l'adresse d'un article et
  une retouche à y faire, Autometa me montre la modification exacte sur cet article seul, sans
  toucher aux autres.

DOD-3 — [du brief : « il faut de la vérification et de la validation »] Aucun article n'est
  modifié dans Zendesk tant que je n'ai pas approuvé la proposition dans un message ultérieur.
  Une proposition que je ne valide pas reste sans effet, indéfiniment.

DOD-4 — [du brief : « changer 100 pages d'un coup »] Quand j'approuve une proposition qui touche
  une centaine d'articles, ils sont tous modifiés, et je reçois le compte de ce qui a été écrit.

DOD-5 — [du brief : « de manière sécurisée »] Si quelqu'un a modifié un article dans Zendesk entre
  ma lecture de la proposition et mon approbation, cet article est laissé tel quel, il m'est
  nommé, et les autres sont modifiés normalement.

DOD-6 — [du brief : « un système d'exports / de sauvegardes avant modifs »] Après une
  modification appliquée, je peux demander de la défaire : chaque article retrouve exactement son
  texte d'avant, sauf ceux retouchés à la main depuis, qui sont laissés tels quels et nommés.

DOD-7 — [du brief : « exports »] Quand je demande un export de l'aide, je reçois un lien pour
  télécharger l'ensemble des articles avec leur contenu.

DOD-8 — [du brief : « on va avoir besoin de ABC »] Je peux demander de créer un article, une
  rubrique ou une catégorie, ou de déplacer un article, de changer ses étiquettes ou de le publier
  ou dépublier. Un article créé est un brouillon tant que je n'ai pas demandé sa publication.

DOD-9 — [du brief : « regarde cette URL »] Quand une proposition ne changerait rien (le mot
  cherché n'apparaît nulle part, la retouche laisse l'article identique), Autometa me le dit et
  aucune proposition n'est créée.

DOD-10 — [du brief : « pas de table dans l'appli », « pas faire grossir le S3 pour rien »] Les
  propositions et leurs sauvegardes ne contiennent que les articles touchés, et aucune sauvegarde
  complète n'est prise sans que je la demande.

DOD-11 — Le texte cherché est pris au pied de la lettre : la casse et les accents comptent, la
  ponctuation n'a aucun sens spécial. Si je demande explicitement une expression régulière, la
  proposition me le rappelle.

DOD-12 — Quand le texte cherché est vide, Autometa refuse et ne crée aucune proposition.

DOD-13 — Quand l'adresse que je donne ne désigne pas un article (rubrique, article supprimé,
  identifiant inconnu), Autometa me le dit et ne crée aucune proposition ; il ne devine pas un
  article voisin.

DOD-14 — Approuver une proposition déjà appliquée, ou défaire une modification jamais appliquée
  ou déjà défaite, n'écrit rien : Autometa me dit dans quel état elle est.

DOD-15 — Quand l'application s'interrompt avant la fin (panne réseau, quota Zendesk), les
  articles déjà écrits sont connus d'Autometa : je peux les défaire, et la proposition me dit
  lesquels restent.

DOD-16 — Quand le texte cherché apparaît aussi dans le nom d'une rubrique ou d'une catégorie, la
  proposition me les nomme, sans les modifier.

DOD-17 — Le remplacement ne touche que le texte visible des articles. Quand le texte cherché
  apparaît dans une adresse de lien, une image ou un autre attribut HTML, il n'y est pas remplacé ;
  la proposition me nomme ces occurrences, article par article, et elles ne sont remplacées que si
  je le demande explicitement.

## Sources lues

- `lib/zendesk.py`, `tests/test_zendesk.py`, `skills/zendesk_query/SKILL.md` — **R1** : le client
  existant est en lecture seule et ne couvre que les tickets. La base de connaissance (Guide)
  n'est atteinte par aucune méthode ; il n'existe pas de brouillon côté serveur pour un article
  déjà publié sur ce plan Zendesk (Suite Professional), ni d'API d'historique des révisions. La
  relecture et le retour arrière doivent donc être portés par Autometa, d'où `DOD-3`, `DOD-5` et
  `DOD-6`.
- `web/s3.py`, `lib/job_inputs.py` — **R1** : le dépôt sait déjà déposer un fichier sur S3 et en
  rendre un lien de téléchargement temporaire, ce qui porte `DOD-7` et le stockage des propositions
  (`DOD-10`).
- `skills/publish_dashboard/SKILL.md` — **R5** : la règle « confirmer explicitement la cible avec
  l'utilisateur avant d'écrire » est le précédent du dépôt pour `DOD-3` et `DOD-8`.
- API Zendesk, sondée le 2026-09-10 et le 2026-09-11 avec le jeton de production — **R2** :
  229 articles (3 requêtes de 100, 1,5 s), 265 Kio une fois compressés ; la suppression, la
  création en brouillon et la réécriture d'un article ont été vérifiées sur la catégorie « Bac a
  sable des emplois ». Le compteur de la recherche Zendesk (224) exclut les brouillons, la liste
  complète (229) les inclut. Les mesures de `DOD-4` et `DOD-7` viennent de là.

Aucun terme IAE, aucun tableau de bord : **R3** et **R4** ne se déclenchent pas.

## Questions ouvertes

Aucune.

Propositions de la lentille gap-hunter écartées, avec la raison :

- plafonner le nombre d'articles d'une proposition : le brief demande explicitement cent pages
  d'un coup sur une base qui en compte 229 ;
- la désignation obligatoire de la proposition en cas d'ambiguïté, la question sur l'emplacement
  d'une création et l'alerte sur un homonyme relèvent de la conduite de la conversation, écrite
  dans le skill, qu'aucun test ne sait démontrer ;
- durée de conservation et attribution nominative : hors du brief, rien n'efface les propositions
  et un lien de téléchargement se redemande.

## Validation

Validé par LJ le 2026-09-11.

Cinq décisions soumises. Quatre défauts retenus : texte cherché littéral, brouillons inclus et
intitulés de rubriques seulement nommés, avancement enregistré article par article, historique
réécrit pour placer le contrat avant le code déjà écrit. Une décision inversée par le demandeur :
les occurrences dans les liens et attributs HTML ne sont pas remplacées sans demande explicite
(`DOD-17`).
