# Favoris personnels sur l'accueil

Statut : en attente de validation.
Validé par : _(à remplir par la personne qui a demandé la fonctionnalité)_

## Ce que je veux

Chacun doit pouvoir se composer son propre accueil. Aujourd'hui l'accueil est le même
pour tout le monde : une zone « Épinglés » alimentée par les admins, et une zone
« Sources de données » qui pointe vers les fiches de connaissance. Rien qui m'appartienne.

Je veux marquer d'une étoile les conversations, les rapports et les tableaux de bord
que je consulte souvent, les retrouver sur l'accueil, et les ranger dans l'ordre qui
m'arrange. La zone « Sources de données » cède la place à cette zone « Favoris » ;
les fiches de connaissance restent accessibles depuis le menu de gauche.

Cette zone est un lanceur, pas un inventaire : des tuiles où je clique pour repartir
là où je vais souvent. Je sais déjà ce que contient un favori — son auteur et sa date
n'ont rien à m'apprendre. Les « Épinglés » gardent leur présentation en liste, ce qui
distingue à l'œil le choix éditorial des admins de ce qui m'appartient.

Mes favoris sont les miens : personne d'autre ne les voit. L'épingle des admins, elle,
ne change pas — c'est un choix éditorial visible par tous, et les deux gestes restent
deux boutons séparés.

## Ce qui devra marcher

DOD-1 — Quand je clique sur l'étoile d'une ligne dans la liste des conversations,
  alors l'étoile se remplit et l'élément apparaît dans « Favoris » sur l'accueil.

DOD-2 — L'étoile est disponible sur les conversations, les rapports et les tableaux
  de bord, aux quatre endroits où on les rencontre : les listes de la page
  Conversations, la liste de la page Tableaux de bord, la fiche d'un tableau de bord,
  et l'en-tête d'une conversation ouverte (ou d'un rapport).

DOD-3 — Quand je clique sur une étoile déjà pleine, alors l'élément quitte mes favoris,
  et il a disparu de l'accueil à ma visite suivante.

DOD-4 — Mes favoris ne sont visibles que par moi. Quand un collègue se connecte avec
  son compte, alors il voit ses propres favoris et aucun des miens.

DOD-5 — L'accueil n'affiche plus la zone « Sources de données ». À sa place figure
  la zone « Favoris ». Un lien « Connaissances » apparaît dans le menu de gauche, dans la zone inférieure, et mène à la page qu'atteignait cette zone.

DOD-6 — Quand je n'ai encore aucun favori, alors la zone « Favoris » reste affichée
  et m'indique comment en ajouter, au lieu de disparaître.

DOD-7 — La zone « Épinglés » reste affichée au-dessus de « Favoris », et son contenu
  est le même pour tout le monde.

DOD-8 — En tant qu'administrateur, l'épingle et l'étoile sont deux boutons distincts :
  quand j'épingle un élément, alors il n'entre pas dans mes favoris ; quand je le mets
  en favori, alors il n'apparaît pas dans « Épinglés ».

DOD-9 — Quand je fais glisser un favori à une autre place dans la zone « Favoris »,
  alors il y reste, et je retrouve cet ordre à ma visite suivante.

DOD-10 — Quand une conversation, un rapport ou un tableau de bord que j'avais mis en
  favori est supprimé, alors la zone « Favoris » s'affiche sans erreur et sans cette
  tuile.

DOD-11 — La zone « Favoris » se présente en grille de tuiles : une icône et un titre
  par tuile, sans auteur ni date. Le titre s'affiche sur deux lignes s'il en a besoin ;
  au-delà il est tronqué à l'écran, et lisible en entier au survol.

## Comment chaque critère se démontre

Le dépôt n'a pas encore de parcours de navigateur — L3 arrive avec le paved road, dont
les PR ne sont pas fusionnées. Les critères qui s'y joueraient se démontrent en attendant
par un test d'API doublé d'une vérification à l'écran consignée dans la PR. La borne de
cinq parcours de navigateur reste tenue d'avance : ils seraient trois.

| Critère | Forme de preuve |
|---|---|
| DOD-1 | Test d'API, puis vérification à l'écran (parcours navigateur quand L3 existera) |
| DOD-2 | Test de rendu : le bouton est présent dans les quatre gabarits |
| DOD-3 | Test d'API, puis vérification à l'écran (parcours navigateur quand L3 existera) |
| DOD-4 | Test d'API : deux utilisateurs, listes disjointes |
| DOD-5 | Test de rendu : absence de la zone, présence du lien de menu |
| DOD-6 | Test de rendu : utilisateur sans favori |
| DOD-7 | Test de rendu : les deux zones, dans cet ordre |
| DOD-8 | Test d'API : épingler n'écrit pas dans les favoris, et réciproquement |
| DOD-9 | Test d'API sur l'ordre persisté, puis vérification du glisser-déposer à l'écran |
| DOD-10 | Test de rendu : favori pointant vers un élément supprimé |
| DOD-11 | Test de rendu : grille, deux lignes de titre, titre complet porté par l'attribut de survol |

DOD-2 ne passerait pas par le navigateur même une fois L3 disponible : vérifier la
présence d'un bouton dans quatre gabarits par quatre parcours coûte cher pour une preuve
que le test de rendu établit aussi bien.

## Questions ouvertes

- **Les rapports sont dans le périmètre alors qu'ils sont candidats à la suppression.**
  Demande explicite : l'étoile doit y figurer comme ailleurs, sinon son absence se
  remarque dans une liste qui porte déjà l'épingle admin. Si les rapports disparaissent,
  leurs favoris disparaissent avec eux — c'est déjà le comportement de DOD-10.

- **Le glisser-déposer sur mobile n'est pas couvert.** Le produit s'utilise au bureau ;
  le glisser-déposer natif du navigateur ne répond pas au tactile. Sur mobile, l'ordre
  reste celui défini au bureau, et l'ajout comme le retrait fonctionnent normalement.
  Si le besoin apparaît, il se traite séparément.

- **Deux lignes de titre, pas plus.** Les titres de conversations sont générés et
  souvent verbeux. Deux lignes absorbent la grande majorité d'entre eux ; au-delà, la
  troncature et le survol prennent le relais (DOD-11). La borne est fixe : des tuiles
  qui s'agrandissent au gré du titre le plus long désalignent la grille et lui font
  perdre ce pour quoi on l'a choisie.

- **Un rapport archivé reste-t-il en favori ?** Retenu par défaut : oui, il reste, car
  l'archivage n'est pas une suppression. À corriger si l'usage montre le contraire.
