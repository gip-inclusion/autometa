# Rétro — menu de filtres clair + recherche par le sens

Le besoin s'est élargi en cours de route : d'abord un simple découpage en deux PR (menu, puis
recherche sémantique), puis « tout dans la PR » avec plusieurs commits. L'align a bien tenu : les
douze critères étaient posés et validés avant la première ligne de code, et les trois tranches
(facettes, menu, recherche) ont suivi le contrat sans dérive.

Ce qui a frotté :

- **La suite hermétique au commit est lente** (plusieurs minutes par commit). Les gros commits ont
  dépassé le délai d'exécution en avant-plan ; il a fallu les lancer en arrière-plan. C'est le point
  qui a le plus coûté en temps d'attente.
- **La base de test locale était périmée** (colonne `tags.description` absente) : `init_db` fait un
  `create_all` qui n'altère pas une table existante, donc une base créée avant une migration reste
  en retard. Il a fallu la recréer. Piège discret, non signalé.
- **L'ordre TDD sur du code déjà écrit** : pour la tranche du menu, le code était en place avant les
  tests d'interface ; il a fallu remiser le code pour journaliser un rouge sincère. Écrire le test
  d'abord, vraiment, aurait évité ce détour.
- **Découverte utile** : l'ancien menu affichait des catégories (`product`, `type_demande`) qui
  n'existaient plus dans la taxonomie — c'était la vraie cause du « les noms ne sont pas clairs ».
  Sans lecture du code existant (R1), le contrat serait passé à côté.

Ce qui a bien marché : l'infrastructure d'embeddings existait déjà (table + cron), la PR n'a fait
que la brancher sur la recherche. La lentille de cohérence n'a trouvé aucun bloqueur.

Coût : parcours long, surtout en attente des suites de tests au commit et des rebuilds.
