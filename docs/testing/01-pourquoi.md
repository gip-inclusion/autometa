# Pourquoi on fait tout ça (sans jargon)

Ce document s'adresse à tout le monde, technique ou non. Il explique la **philosophie** de notre stratégie de test : pas les outils, l'idée. Si tu ne lis qu'un document, c'est celui-ci.

## Le problème de départ

Ce logiciel est développé en grande partie par des agents IA. Une IA écrit vite, mais elle a deux travers connus :

1. elle peut **casser sans le voir** une fonctionnalité qui marchait (une régression) ;
2. elle peut écrire un test qui **fait semblant** de vérifier quelque chose — il s'exécute, il est « vert », mais il ne contrôle rien de réel. On appelle ça du *slop* : du remplissage qui ressemble à du sérieux.

Un test vert ne prouve donc pas grand-chose en soi. Toute la stratégie consiste à rendre le mot « testé » digne de confiance.

## L'idée-clé : règle contre loi

Quand on écrit une consigne (« il faut tester ton code »), c'est un **espoir** : l'agent peut la suivre, l'oublier, ou la contourner. Quand on met en place une vérification automatique qui **bloque** si la consigne n'est pas respectée, c'est une **loi** : ce n'est plus négociable.

> Poser des règles, c'est bien. Se donner les moyens de **vérifier tout seul, mécaniquement**, qu'elles sont respectées, c'est ce qui change tout.

Toute la stratégie, c'est transformer nos règles d'espoirs en lois.

## La dette : la regarder en face

Le code qui existe aujourd'hui, on le considère comme une **dette qu'on assume**. On ne se ment pas en disant qu'il est parfaitement testé. On le regarde en face : *il y a là-dedans des choses mal couvertes, on ne sait même pas toutes lesquelles, et on n'a pas les moyens de tout reprendre maintenant.*

À partir de ce constat honnête, la stratégie n'est **pas** « rendre tout propre d'un coup ». C'est, dans l'ordre :

1. **empêcher la dette de grossir**,
2. **geler son niveau** pour qu'elle n'empire jamais,
3. **et seulement ensuite, la rembourser** — chaque morceau remboursé étant **verrouillé pour de bon**, jamais à repayer.

C'est tout. Le reste, ce sont les outils pour tenir ces trois promesses.

## Comment ça se déroule, étape par étape

**1. On trace une ligne au niveau d'aujourd'hui, et on jure : jamais en dessous.**
On mesure la qualité actuelle, et ce niveau devient le sol. On ne dit pas qu'il est bon — on dit « c'est notre dette acceptée, et désormais elle ne peut plus empirer ». Le passé est gelé.

**2. On surveille uniquement le travail neuf.**
Le sol a un défaut : il regarde la *moyenne*. On pourrait ajouter du code bâclé sans que la moyenne bouge — le sol ne le verrait pas. Donc on ajoute une règle qui ne juge plus l'ensemble, mais **chaque nouveauté isolément** : tout ce qu'on ajoute doit être irréprochable en soi. Résultat : **la dette ne peut plus grossir**, parce que rien de neuf n'a le droit d'en rajouter.

> À ce stade, avec presque rien, on a déjà gagné l'essentiel : le passé ne peut plus empirer, le futur ne peut plus salir. La dette est devenue une quantité **figée et finie**. Elle ne peut plus que diminuer.

**3. On vérifie que « il y a un test » veut dire « le test vérifie vraiment quelque chose ».**
Un test peut faire tourner le code sans rien contrôler. On met un garde qui repère ces tests-fantômes. Maintenant « le neuf est testé » signifie testé **pour de vrai**, pas sur le papier.

**4. On rapproche les vérifications du moment où on écrit.**
Jusque-là, tout se contrôle à la fin, quand on rend le travail : tard, et coûteux à corriger. On colle les mêmes contrôles juste à côté de celui qui écrit — humain ou agent — pour attraper l'erreur en quelques secondes au lieu de la découvrir à la fin. Mêmes lois, juste plus tôt et moins cher.

**5. On range pour que ça tienne quand le volume grossit.**
À mesure que l'agent ajoute, un tas de tests en vrac pourrit. On organise pour que, pour n'importe quel morceau de code, il y ait une **place évidente** où vit son test — la question « est-ce testé ? » devient répondable d'un coup d'œil, même par une machine.

**6. On commence à rembourser, en rendant certaines erreurs carrément impossibles.**
Pour toute une famille de fautes, on n'écrit même pas de test : on arrange les choses pour que la faute **ne puisse plus s'exprimer du tout**. On démarre sur le petit cœur critique, on élargit ensuite, et chaque zone sécurisée ainsi ne peut plus jamais se rouvrir.

**7. On vérifie enfin que nos tests *mordent*, et que les chiffres sont justes.**
Un test peut passer et rester faible ; une analyse peut être parfaitement plombée et afficher de **faux chiffres**. À la fin, on mesure la force réelle des tests, et on contrôle l'exactitude des données — les deux choses qu'un « tout est vert » peut encore cacher.

## L'essence, en une phrase

> On regarde la dette en face, on l'empêche de grossir, on gèle son niveau — puis on la rembourse porte par porte, et **chaque porte fermée est verrouillée pour toujours**. On ne paie jamais deux fois la même dette, et on n'en laisse jamais entrer de nouvelle.

## Pourquoi c'est progressif (et pourquoi c'est une force)

On peut **s'arrêter après n'importe quelle étape** en étant strictement plus sûr qu'avant. Il n'y a pas de « big bang » à réussir d'un coup. Chaque étape apporte un gain isolé et définitif. C'est ce qui rend la démarche tenable dans un repo vivant, sans jamais tout bloquer.
