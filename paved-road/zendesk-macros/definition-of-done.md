# Consulter et modifier les macros Zendesk depuis Autometa

## Ce que je veux

Pouvoir demander à Autometa de consulter les macros du support des Emplois et de les modifier, une
à une ou en masse, sans passer par l'interface Zendesk. Mêmes garanties que pour l'aide en ligne :
rien ne s'écrit sans que j'aie vu et validé ce qui va changer, et je peux revenir en arrière.

## Ce qui devra marcher

DOD-1 — [du brief : « consulter les macros »] Quand je demande les macros, Autometa me les présente
  rangées par catégorie, actives et inactives distinguées, avec pour chacune son nombre
  d'utilisations sur les trente derniers jours. La catégorie est la partie du titre avant le premier
  `::` ; les macros sans `::` sont rangées en dernier, sous « Sans catégorie ».

DOD-2 — [du brief : « consulter … individuellement »] Quand je donne l'adresse ou l'identifiant
  d'une macro, Autometa m'en montre le titre, la description, l'état actif ou inactif, à qui elle
  est réservée s'il y a lieu, le texte de réponse et chacune des autres actions. Les statuts,
  groupes, agents et champs de ticket sont désignés par leur nom ; « l'agent qui applique la macro »
  est dit en clair ; un élément supprimé depuis apparaît comme « inconnu » avec son numéro, jamais
  omis.

DOD-3 — [du brief : « éditer … en batch », « même principe que la documentation »] Quand je demande
  de remplacer un mot ou une expression dans les macros, Autometa me présente la liste des macros
  qui changeraient, inactives comprises, avec pour chacune ce qui est retiré et ce qui est ajouté,
  montré au niveau du paragraphe modifié et non de la réponse entière, et rien n'est encore modifié
  dans Zendesk. Le remplacement porte sur le titre, la description, le sujet et le texte de réponse.

DOD-4 — [du brief : « éditer … en batch »] Quand je demande une modification en masse qui n'est pas
  un remplacement de texte — désactiver toutes les macros d'une catégorie, remplacer une étiquette
  par une autre —, Autometa me présente de la même façon chaque macro touchée avec l'avant et
  l'après de ce qui change. Une catégorie est désignée exactement : « Prolongation » ne désigne pas
  « Prolongations ».

DOD-5 — [du brief : « éditer … individuellement »] Quand je donne l'adresse d'une macro et une
  retouche à y faire, Autometa me montre la modification exacte sur cette macro seule, sans toucher
  aux autres.

DOD-6 — [du brief : « même principe que la documentation »] Aucune macro n'est modifiée dans
  Zendesk tant que je n'ai pas approuvé la proposition dans un message ultérieur. Une proposition
  que je ne valide pas reste sans effet, indéfiniment.

DOD-7 — [du brief : « en batch »] Quand j'approuve une proposition qui touche toutes les macros
  (322 aujourd'hui), elles sont toutes modifiées, et je reçois le compte de ce qui a été écrit.

DOD-8 — [du brief : « même principe que la documentation »] Si quelqu'un a modifié ou supprimé une
  macro dans Zendesk entre ma lecture de la proposition et mon approbation, cette macro est laissée
  telle quelle, elle m'est nommée avec la raison, et les autres sont modifiées normalement. Un
  simple changement de place dans la liste ne compte pas comme une modification.

DOD-9 — [du brief : « même principe que la documentation »] Après une modification appliquée, je
  peux demander de la défaire : chaque macro retrouve exactement son titre, sa description, son état
  et ses actions d'avant, sauf celles retouchées à la main ou supprimées depuis, qui sont laissées
  telles quelles et nommées. Une macro supprimée n'est jamais recréée.

DOD-10 — [du brief : « éditer »] Je peux demander de créer une macro : Autometa me montre la macro
  qu'il va créer et ne la crée qu'après mon accord dans un message ultérieur. Elle est créée
  inactive tant que je n'ai pas demandé son activation. Autometa ne supprime jamais une macro ; pour
  en retirer une, il la désactive.

DOD-11 — Quand une proposition ne changerait rien (l'expression cherchée n'apparaît nulle part, la
  retouche laisse la macro identique), Autometa me le dit et aucune proposition n'est créée.

DOD-12 — Le texte cherché est pris au pied de la lettre : la casse et les accents comptent, la
  ponctuation n'a aucun sens spécial. Si je demande explicitement une expression régulière, la
  proposition me le rappelle. Un texte cherché vide est refusé, sans proposition.

DOD-13 — Quand l'adresse ou l'identifiant que je donne ne désigne pas une macro (article de l'aide,
  macro supprimée, identifiant inconnu), Autometa me le dit et ne crée aucune proposition ; il ne
  devine pas une macro voisine.

DOD-14 — Approuver une proposition déjà appliquée, ou défaire une modification jamais appliquée ou
  déjà défaite, n'écrit rien : Autometa me dit dans quel état elle est.

DOD-15 — Quand l'application s'interrompt avant la fin (panne réseau, quota Zendesk), les macros
  déjà écrites sont connues d'Autometa : je peux les défaire, et la proposition me dit lesquelles
  restent.

DOD-16 — Le remplacement ne touche que le texte que lit l'usager. Quand le texte cherché apparaît
  dans une adresse de lien, un attribut HTML, une variable ou une instruction Zendesk
  (`{{ticket.id}}`, `{% if … %}`, `{{dc.…}}`), il n'y est pas remplacé ; la proposition me nomme ces
  occurrences, macro par macro, et elles ne sont remplacées que si je le demande explicitement.

DOD-17 — Une proposition porte soit sur des macros, soit sur des articles de l'aide, jamais les
  deux, et le dit. Approuver une proposition sur les macros n'écrit aucun article, et
  réciproquement.

DOD-18 — [du brief : « consulter »] Quand je demande un export des macros, je reçois un lien pour
  télécharger l'ensemble des macros avec toutes leurs actions.

DOD-19 — Remplacer une étiquette ne touche que l'étiquette entière : remplacer « ntt » ne modifie
  pas « nia-ntt ». Une macro qui portait déjà la nouvelle étiquette ne l'a pas en double. Une
  étiquette contenant une espace est refusée, sans proposition.

DOD-20 — Le texte est cherché tel qu'il s'affiche : « Pass IAE » trouve aussi « Pass IAE » écrit
  avec une espace insécable, et un guillemet trouve un guillemet codé en HTML. Les espaces
  insécables qui ne sont pas dans le texte cherché restent en place.

## Sources lues

- `lib/zendesk.py`, `lib/zendesk_changeset.py`, `skills/zendesk/SKILL.md`, `tests/test_zendesk.py`,
  `tests/test_zendesk_changeset.py` — **R1** : le client lit et modifie les articles de l'aide via
  des propositions figées sur S3, validées puis appliquées sous garde, réversibles. Aucune méthode
  n'atteint les macros. La garde, la reprise après interruption et le retour arrière sont propres
  aux articles (titre et corps), d'où `DOD-8`, `DOD-9`, `DOD-15` et `DOD-17`. Un article supprimé
  entre-temps tombe aujourd'hui en erreur réessayée sans fin, d'où la raison « supprimée » de
  `DOD-8` et `DOD-9`.
- `paved-road/zendesk-write/definition-of-done.md` — **R5** : le contrat de l'édition des articles,
  dont ce parcours reprend les garanties (« même principe ») et les décisions : texte littéral,
  brouillons (ici macros inactives) inclus, balisage HTML protégé par défaut, avancement enregistré
  élément par élément, création hors proposition après confirmation.
- API Zendesk, sondée le 2026-10-02 avec le jeton de production (rôle admin) — **R2** : 322 macros
  dont 261 actives, lues en 4 requêtes de 100 (2 s), 568 Kio bruts et 94 Kio compressés ;
  304 portent un texte de réponse HTML, **tous sur une seule ligne** (médiane 673 caractères), d'où
  le diff par paragraphe de `DOD-3` ; 266 contiennent des entités HTML (2 024 `&nbsp;`, 108
  `&quot;`), d'où `DOD-20` ; 4 contiennent des variables Zendesk, aucune `{% %}` ni `{{dc.}}`
  aujourd'hui ; `raw_title` identique à `title` pour les 322 ; 308 titres ont au moins une catégorie
  (`::`), 42 catégories de premier niveau, dont des voisines (« Prolongation » et
  « Prolongations », « PASS » et « Pass IAE ») ; les étiquettes sont des listes séparées par des
  espaces (`nia-7et8 ntt nia-ntt`) ; 3 macros réservées à un groupe ou un agent ; le compteur
  d'utilisation sur 30 jours est fourni par l'API (179 macros actives à zéro). Autres actions :
  assignation (315), statut (187), statut personnalisé (66), sujet (27), étiquettes (44), marque
  (17), champs personnalisés (12).

Aucun terme IAE, aucun tableau de bord : **R3** et **R4** ne se déclenchent pas.

## Questions ouvertes

Aucune.

Propositions de la lentille gap-hunter écartées, avec la raison :

- annuler une création par désactivation, et éviter un doublon à la reprise d'une création : la
  création ne passe pas par une proposition (comme pour les articles), elle est confirmée puis faite
  en un appel ;
- « changer le statut » réservé aux macros qui posent déjà un statut, un nom de statut ou de groupe
  ambigu, un titre vidé par un remplacement, l'alerte sur un titre déjà pris ou une catégorie
  nouvelle : conduite de la conversation, écrite dans le skill ;
- verrou contre deux approbations simultanées : même consigne que pour les articles, écrite dans le
  skill ; le stockage n'offre pas d'écriture conditionnelle sur laquelle l'asseoir sans table ;
- titre saisi (`raw_title`) plutôt qu'affiché : identiques sur les 322 macros, aucun contenu
  dynamique dans les titres.

## Validation

Validé par LJ le 2026-10-02.

Trois décisions prises avant rédaction : une proposition peut modifier toute la macro (titre,
description, état, actions) ; créer oui, supprimer jamais ; parcours paved road. Quatre défauts
soumis et retenus : texte cherché tel qu'il s'affiche (`DOD-20`), liens, attributs et variables
protégés sauf demande explicite (`DOD-16`), macro supprimée jamais recréée (`DOD-9`), étiquette
remplacée entière (`DOD-19`).
