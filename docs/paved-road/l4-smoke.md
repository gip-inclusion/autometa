# L4 — la passe de smoke

Ce que les tests ne voient pas : l'écran. Un test vérifie ce qu'on a pensé à vérifier ; le smoke
regarde ce qu'aucun test n'avait prévu — un bouton qui ne se voit pas, un texte tronqué, une page
qui met dix secondes, un lien qui mène ailleurs.

## Quand une passe est due

`scripts/smoke.py plan` tranche seul. Il compare le diff à la base et déclare une passe due si la
branche touche une surface d'interface : un template, un fichier statique, une route. Sinon il ne
demande rien — un changement de calcul dans `lib/` n'a rien à montrer.

`plan` calcule aussi une **empreinte de l'interface** et refuse une seconde passe sur la même :
une passe de smoke coûte une session avec un humain présent, la refaire sur un écran inchangé
n'apprend rien.

D'où l'ordre imposé à Review : lentille, corrections, **puis** smoke. Une correction faite après
la passe rouvrirait une empreinte, donc une passe.

## Ce que l'agent produit

Un `rapport.md` sous `~/.cache/autometa/smoke/<branche>/<empreinte>/`, **hors du dépôt**, avec une
capture par critère observable. `scripts/smoke.py verify` refuse un rapport absent, et refuse tout
binaire committé : le dépôt est public, et une capture d'écran d'une application de données montre
des données.

Le rapport dit ce qui a été regardé et ce qui a été vu. Quand un critère ne se voit pas en une
passe — il en faut deux, ou deux jours — le rapport le dit et renvoie au test qui le démontre.

## La limite, écrite franchement

Le smoke pilote le navigateur de la machine via l'extension Claude in Chrome : **il exige une
session interactive, avec un humain présent**. C'est la seule étape du parcours qui ne tourne pas
la nuit. Un parcours lancé sans personne devant s'arrête là.

Ce n'est pas un oubli, c'est le prix de regarder un écran plutôt que d'affirmer qu'on l'a regardé.
La bascule sur un navigateur sans tête est prévue au palier 3 ; d'ici là, la review app donne au
pair le moyen d'essayer lui-même, plus tard dans le parcours.

## Ce que le smoke ne fait pas

Il ne démontre aucun critère. Une preuve est une commande rejouable (L1) ; une passe de smoke est
un regard, elle ne se rejoue pas et son verdict ne devient jamais un check. Un critère qui ne peut
être démontré que par un œil humain est un critère mal écrit — il faut le reformuler en résultat
observable par une commande, ou l'assumer comme non démontré dans la description de PR.
