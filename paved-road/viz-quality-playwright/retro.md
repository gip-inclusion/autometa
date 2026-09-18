# Rétro — viz-quality-playwright

Ce parcours n'en est pas un au sens propre : la fonctionnalité était construite, poussée et en PR
(#228, CI verte) avant que le parcours soit ouvert. On a demandé à l'agent de mettre la PR « au
format paved road ». Il l'a fait sans réécrire le code, et le dispositif l'a refusé exactement là où
il devait : l'antériorité du contrat. Rien n'a été contourné, et c'est la seule issue honnête.

**Ce qui a frotté.** Trois contrôles butent sur un retro-fit, et aucun n'a de sortie légitime.
L'antériorité (`verify_dod`) ne se répare que par une réécriture d'historique, interdite sur une
branche poussée — pourtant elle s'annonce en famille A, « réparable — corriger et relancer ». Pour un
agent qui prend l'étiquette au mot, c'est une invitation à reconstruire la branche dans l'ordre
voulu ; ce serait blanchir le signal que le contrôle protège. Un parcours ouvert après le code
devrait sortir en famille C (question au demandeur), pas A. Même chose pour le rouge : un test qui
passe déjà ne peut plus être vu échouer honnêtement, et renommer les tests existants en
`test_dod_N_…` ne ferait que déplacer le problème. Les dix critères restent donc « non démontrés »
au sens du parcours, alors que 25 tests unitaires et 2 tests navigateur couvrent déjà la plupart
d'entre eux. Enfin, le skill dit d'écrire les frictions « dans le journal du parcours », mais le
journal n'est écrit que par `advance` : elles sont ici, dans la rétro.

**Ce qui a surpris.** Les deux lentilles ont payé, même après coup. La chasse aux trous a trouvé
cinq comportements réels que personne n'avait nommés (graphiques masqués non vérifiés, diagnostic
« navigateur absent ? » sur une page lente, nombre de graphiques oublié…). La relecture de cohérence
a trouvé que le contrat promettait plus que le code (livraison d'un TDB cassé, `DOD-8` « en
entier ») : les deux fois, c'est le contrat qui a été corrigé, parce qu'il avait été écrit en
regardant le code et en reprenant l'intention du brief plutôt que ce que le code fait. C'est
précisément le biais d'un contrat rétroactif : il décrit l'idéal, puis se fait rattraper par le réel.

**Ce qui a coûté du temps.** Lire `lib/attestation.py` pour savoir d'avance ce qui refuserait,
plutôt que de le découvrir à l'essai. Deux remarques pour un parcours suivant : deux vérifications
simultanées du même TDB écrivent la même capture (`/tmp/verify_dashboard/<slug>.png`), et une
vérification par URL qui tombe sur la page de connexion n'est pas identifiée comme telle.

**Coût.** `/cost` n'est pas accessible depuis une session pilotée par clawdio ; ordre de grandeur :
une session, trois sous-agents de lecture (≈ 110 k jetons à eux trois).
