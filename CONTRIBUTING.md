# Contribuer

## Démarrer de zéro

```bash
# 1. Cloner le repo et s'y placer
git clone https://github.com/votre-org/autometa.git
cd autometa

# 2. Installer l'environnement de développement
make setup

# 3. Vérifier que tout est en place — chaque échec est une phrase actionnable
make doctor

# 4. Lancer Claude Code
claude
```

## Développer une fonctionnalité

Le projet suit le **paved road** : un parcours unique, qui ajoute une contrainte à la fois. Sa
conception et sa justification sont dans `docs/plans/2026-07-28-autometa-paved-road-design.md`.

Les niveaux L0, L1 et L2 sont en place. L0 (l'accord écrit) se tient **à la main** ; L1 (les
attestations) s'outille par quatre cibles du `Makefile`, qui refusent de faire progresser le parcours
sans code de sortie 0 ; L2 est armé, c'est-à-dire que la CI refuse le merge quand ils manquent.
Détail : `docs/paved-road/l2-quality-gates.md`.

1. **Écrire la Definition of Done avant de coder.** Un fichier
   `paved-road/<nom-de-branche>/definition-of-done.md` qui dit, en français, ce qui devra marcher à
   la fin. Format et règles : `docs/paved-road/l0-definition-of-done.md`.
2. **La faire valider** par la personne qui a formulé la demande, en lui soumettant au plus cinq
   décisions, chacune avec un défaut déjà choisi. Ne rien dire, c'est accepter le défaut.
3. **Committer la DoD en premier.** Le premier commit de la branche est celui qui l'ajoute : c'est la
   seule chose qui distingue un accord convenu d'avance d'une DoD écrite après coup pour coller au
   code produit.
4. **Coder**, puis démontrer chaque critère par une commande réelle :
   `make paved-road-advance DOD=DOD-1 CMD='…'` range l'attestation correspondante — la commande, son
   code de sortie, les empreintes du contenu prouvé, le verdict. Format et règles :
   `docs/paved-road/l1-attestation.md`.
5. **Ouvrir la PR** avec la DoD, le journal et les attestations dedans.

`make paved-road-status` dit à tout moment l'état atteint et quels critères restent à démontrer.
Aucune image et aucun binaire sous `attestations/` : le dépôt est public, et un check le refuse.

## Ce que la CI exige, et quand

Le check **« Ce qui devait marcher »** est requis **si et seulement si** votre diff touche `web/`,
`lib/`, `skills/` ou `alembic/`. Sur ce périmètre, l'absence de Definition of Done est un échec.
Ailleurs — dépendances, `docs/`, `knowledge/` — il est neutre et ne demande rien.

La CI **rejoue** les commandes de vos attestations et compare son résultat au verdict que vous y avez
écrit : un écart est un échec. Une attestation devient aussi caduque quand le code qu'elle prouve
change. Chaque échec restitué porte sa famille — A réparable, B panne d'environnement, C question
métier, D interdit — parce que la réponse n'est pas la même.

Pour lever le check sur une PR qui n'a pas à passer par le parcours, un humain pose le label
`break-glass` : la dispense est alors journalisée dans le résumé du check.

Vérifier avant de pousser : `make paved-road`, ou `make ci` pour l'ensemble des gates. `make setup`
installe un hook `pre-push` qui lance lint et tests unitaires — un service, pas une garantie :
`--no-verify` le contourne. Pour l'installer seul : `make install-hooks`.

Une DoD validée ne se réécrit pas. Un critère qui se révèle infaisable est un blocage métier : il
remonte à la personne qui a formulé la demande, avec au moins deux options formulées en résultats
observables.

## Les règles que la DoD ne porte pas

Les invariants permanents — SQL paramétré, timeouts, migrations, sécurité — ne se recopient pas dans
chaque Definition of Done. Ils vivent dans `.claude/rules/`, dans `gates.toml` et dans la CI, et
protègent aussi le travail qui ne passe pas par le paved road.
